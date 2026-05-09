from flask import request, jsonify
from flask_login import login_required, current_user

from ..execution_router import resolve_execute_route, validate_schedule_inputs
from ..intents import safe_text_for_log
from ..result_formatter import format_execution_payload, format_error_summary
from ..services import (
    command_validator,
    llm_client,
    logger,
    rag_pipeline,
    security_layer,
    ssh_executor,
)


def register_api_routes(app):
    @app.route('/api/execute', methods=['POST'])
    @login_required
    def execute_command():
        """Main API endpoint for command execution"""
        try:
            data = request.json
            natural_language = data.get('command', '').strip()
            target_servers = data.get('servers', [])

            if not natural_language:
                return jsonify({
                    'error': 'Command is required',
                    'natural_language_summary': format_error_summary(
                        'Please describe what you want in the text box.',
                        details='For example: Show how much disk space is free.',
                    ),
                }), 400

            validation_result = security_layer.validate_input(natural_language)
            if not validation_result['valid']:
                logger.warning(
                    f"Input validation failed for user {current_user.username}: "
                    f"{validation_result['reason']}"
                )
                return jsonify({
                    'error': 'Input validation failed',
                    'reason': validation_result['reason'],
                    'natural_language_summary': format_error_summary(
                        'We could not use that wording for safety reasons',
                        validation_result['reason'],
                    ),
                }), 400

            if not target_servers:
                target_servers = list(app.config['REMOTE_SERVERS'] or [])

            if not target_servers:
                return jsonify({
                    'error': 'No target servers configured',
                    'details': 'Please configure REMOTE_SERVERS in .env or specify servers in the request',
                    'natural_language_summary': format_error_summary(
                        'No computers were selected to run this on',
                        details='Enter host names in the Target Servers box or set REMOTE_SERVERS in your settings file.',
                    ),
                }), 400

            resolved = resolve_execute_route(natural_language, llm_client)

            if resolved.cron_blocked:
                return jsonify({
                    'error': 'Cron removal is blocked in Safe Cron Mode',
                    'natural_language_summary': format_error_summary(
                        'Removing or clearing crontab entries is blocked by policy.',
                        details='You can only list or schedule managed ShellSentry script entries.',
                    ),
                }), 400

            if resolved.archive_forbidden:
                return jsonify({
                    'error': 'Archived script change blocked',
                    'natural_language_summary': format_error_summary(
                        'Changing, deleting, or editing saved archive scripts is not allowed.',
                        details='You can list, re-run, or explain saved scripts; use Safe Cron only for scheduling.',
                    ),
                }), 400

            if resolved.cron_action == 'list':
                execution_results = ssh_executor.list_managed_cron_entries(
                    target_servers,
                    current_user.username,
                    current_user.id,
                    natural_language,
                )
                generated_command = (
                    f"List managed cron entries ({app.config['SAFE_CRON_TAG_PREFIX']}:*)"
                )
                formatted = format_execution_payload(
                    natural_language, generated_command, execution_results, host_context=None
                )
                return jsonify({
                    "success": True,
                    "original_request": natural_language,
                    "generated_command": generated_command,
                    "results": execution_results,
                    "natural_language_summary": formatted["natural_language_summary"],
                    "formatted_report": formatted["formatted_report"],
                    "intent_route_source": resolved.source,
                })

            if resolved.cron_action == 'schedule':
                if not app.config.get('SAFE_CRON_MODE', True):
                    return jsonify({
                        'error': 'Safe Cron Mode is disabled',
                        'natural_language_summary': format_error_summary(
                            'Safe Cron Mode is currently disabled in configuration.',
                        ),
                    }), 400

                script_name = resolved.script_name
                cron_expr = resolved.cron_expr
                sched_ok, sched_reason = validate_schedule_inputs(script_name, cron_expr)
                if not sched_ok:
                    return jsonify({
                        'error': 'Invalid schedule request',
                        'details': sched_reason,
                        'natural_language_summary': format_error_summary(
                            'Could not schedule: missing script name or invalid cron expression.',
                            details=sched_reason,
                        ),
                    }), 400

                servers_with_script, servers_missing_script = ssh_executor.get_servers_having_script(
                    target_servers, script_name
                )
                if not servers_with_script:
                    return jsonify({
                        'error': 'Saved script not found on selected servers',
                        'natural_language_summary': format_error_summary(
                            'Could not find that saved script to schedule.',
                            details=f"Script must exist in $HOME/{app.config['SCRIPT_ARCHIVE_DIR_NAME']} on target servers.",
                        ),
                    }), 400

                execution_results = ssh_executor.schedule_saved_script_cron(
                    servers_with_script,
                    script_name,
                    cron_expr,
                    current_user.username,
                    current_user.id,
                    natural_language,
                )
                generated_command = (
                    f"Schedule managed cron: {cron_expr} "
                    f"bash $HOME/{app.config['SCRIPT_ARCHIVE_DIR_NAME']}/{script_name}"
                )
                formatted = format_execution_payload(
                    natural_language, generated_command, execution_results, host_context=None
                )
                payload = {
                    "success": True,
                    "original_request": natural_language,
                    "generated_command": generated_command,
                    "results": execution_results,
                    "natural_language_summary": formatted["natural_language_summary"],
                    "formatted_report": formatted["formatted_report"],
                }
                if servers_missing_script:
                    payload["missing_script_servers"] = servers_missing_script
                payload["intent_route_source"] = resolved.source
                return jsonify(payload)

            if resolved.archive_action == 'list':
                date_scope = resolved.date_scope or 'all'
                list_day_start = resolved.list_day_start
                execution_results = ssh_executor.list_saved_scripts(
                    target_servers,
                    current_user.username,
                    current_user.id,
                    natural_language,
                    date_scope=date_scope,
                    list_day_start=list_day_start,
                )
                scope_note = date_scope
                if date_scope == 'day' and list_day_start:
                    scope_note = f"day {list_day_start}"
                generated_command = (
                    f"List scripts in $HOME/{app.config['SCRIPT_ARCHIVE_DIR_NAME']} "
                    f"(scope: {scope_note}, max: {app.config['SCRIPT_ARCHIVE_MAX_LIST']})"
                )
                formatted = format_execution_payload(
                    natural_language, generated_command, execution_results, host_context=None
                )
                return jsonify({
                    "success": True,
                    "original_request": natural_language,
                    "generated_command": generated_command,
                    "results": execution_results,
                    "natural_language_summary": formatted["natural_language_summary"],
                    "formatted_report": formatted["formatted_report"],
                    "intent_route_source": resolved.source,
                })

            if resolved.archive_action == 'rerun':
                script_name = resolved.script_name
                if not script_name:
                    return jsonify({
                        'error': 'Script name is required',
                        'natural_language_summary': format_error_summary(
                            'Please include the saved script name',
                            details='Example: Re-run ShellSentry_2026-05-06_13-51-59_123456789.sh',
                        ),
                    }), 400

                servers_with_script, servers_missing_script = ssh_executor.get_servers_having_script(
                    target_servers, script_name
                )
                if not servers_with_script:
                    return jsonify({
                        'error': 'Saved script not found on selected servers',
                        'details': (
                            f"Script `{script_name}` was not found in "
                            f"$HOME/{app.config['SCRIPT_ARCHIVE_DIR_NAME']} on the selected servers."
                        ),
                        'natural_language_summary': format_error_summary(
                            'Could not find that saved script on your selected servers.',
                        ),
                    }), 400

                script_search = ssh_executor.find_saved_script_content_across_servers(
                    servers_with_script, script_name
                )
                if not script_search.get('success'):
                    reason = script_search.get('error', 'Could not read script content for validation')
                    return jsonify({
                        'error': 'Failed to validate saved script',
                        'details': reason,
                        'natural_language_summary': format_error_summary(
                            'Could not validate the saved script before execution',
                            reason=reason,
                        ),
                    }), 400

                script_validation = command_validator.validate(script_search.get('content', ''))
                if not script_validation.get('valid'):
                    reason = script_validation.get('reason', 'Policy validation failed')
                    return jsonify({
                        'error': 'Saved script is blocked by security policy',
                        'reason': reason,
                        'natural_language_summary': format_error_summary(
                            'This saved script is not allowed to run under current restrictions',
                            reason=reason,
                        ),
                    }), 400

                execution_results = ssh_executor.execute_saved_script(
                    servers_with_script,
                    script_name,
                    current_user.username,
                    current_user.id,
                    natural_language,
                )
                generated_command = f"bash $HOME/{app.config['SCRIPT_ARCHIVE_DIR_NAME']}/{script_name}"
                formatted = format_execution_payload(
                    natural_language, generated_command, execution_results, host_context=None
                )

                script_explanation = ""
                sample_server = target_servers[0] if target_servers else None
                if sample_server:
                    script_data = ssh_executor.get_saved_script_content(sample_server, script_name)
                    if script_data.get('success'):
                        exp = llm_client.explain_script(
                            script_name, script_data.get('content', '')
                        )
                        if exp.get('success'):
                            script_explanation = exp.get('explanation', '').strip()

                payload = {
                    "success": True,
                    "original_request": natural_language,
                    "generated_command": generated_command,
                    "results": execution_results,
                    "natural_language_summary": formatted["natural_language_summary"],
                    "formatted_report": formatted["formatted_report"],
                }
                if servers_missing_script:
                    payload["missing_script_servers"] = servers_missing_script
                if script_explanation:
                    payload["script_explanation"] = script_explanation
                payload["intent_route_source"] = resolved.source
                return jsonify(payload)

            if resolved.archive_action == 'explain':
                script_name = resolved.script_name
                if not script_name:
                    return jsonify({
                        'error': 'Script name is required',
                        'natural_language_summary': format_error_summary(
                            'Please include the saved script name',
                            details='Example: Explain ShellSentry_2026-05-06_13-51-59_123456789.sh',
                        ),
                    }), 400

                script_search = ssh_executor.find_saved_script_content_across_servers(
                    target_servers, script_name
                )
                if not script_search.get('success'):
                    reason = script_search.get('error', 'Could not find/read script')
                    return jsonify({
                        'error': 'Failed to read saved script',
                        'details': reason,
                        'natural_language_summary': format_error_summary(
                            'Could not read that saved script',
                            reason=reason,
                        ),
                    }), 400

                exp = llm_client.explain_script(script_name, script_search.get('content', ''))
                if not exp.get('success'):
                    reason = exp.get('error', 'Could not explain script')
                    return jsonify({
                        'error': 'Failed to explain script',
                        'details': reason,
                        'natural_language_summary': format_error_summary(
                            'Could not generate the script explanation',
                            reason=reason,
                        ),
                    }), 500
                return jsonify({
                    "success": True,
                    "original_request": natural_language,
                    "generated_command": f"explain {script_name}",
                    "results": {},
                    "natural_language_summary": (
                        f"Found script `{script_name}` on server {script_search.get('server')}. "
                        "Here is a plain-language explanation."
                    ),
                    "formatted_report": script_search.get('content', ''),
                    "script_explanation": exp.get('explanation', '').strip(),
                    "intent_route_source": resolved.source,
                })

            host_context = ssh_executor.probe_host_context(target_servers)
            logger.info(
                f"User {current_user.username} requested: {safe_text_for_log(natural_language)} "
                f"(host context probe: {len(host_context)} host(s))"
            )

            retrieved_examples = rag_pipeline.retrieve(natural_language, top_k=3)
            rag_context_text = rag_pipeline.format_for_prompt(retrieved_examples)

            llm_response = llm_client.generate_command(
                natural_language,
                remote_host_context=host_context,
                rag_context_text=rag_context_text,
                execution_style=resolved.execution_style,
            )

            if not llm_response['success']:
                err = llm_response.get('error', 'Unknown error')
                return jsonify({
                    'error': 'Failed to generate command',
                    'details': err,
                    'natural_language_summary': format_error_summary(
                        'We could not turn your question into a safe command',
                        err,
                    ),
                }), 500

            generated_command = llm_response['command']
            logger.info(f"Generated command: {generated_command}")

            validation_result = command_validator.validate(generated_command)
            if not validation_result['valid']:
                logger.warning(f"Command validation failed: {validation_result['reason']}")
                return jsonify({
                    'error': 'Command validation failed',
                    'reason': validation_result['reason'],
                    'generated_command': generated_command,
                    'natural_language_summary': format_error_summary(
                        'That command is not allowed to run on your servers',
                        validation_result['reason'],
                    ),
                }), 400

            command_to_run = command_validator.normalize_for_execution(generated_command)

            execution_results = ssh_executor.execute_on_servers(
                command_to_run,
                target_servers,
                current_user.username,
                current_user.id,
                natural_language
            )

            logger.info(
                f"Command executed by {current_user.username} on {len(target_servers)} server(s)"
            )

            formatted = format_execution_payload(
                natural_language, command_to_run, execution_results, host_context
            )

            ai_explain = ""
            summ = llm_client.summarize_execution_report(
                natural_language,
                command_to_run,
                formatted["formatted_report"],
            )
            if summ.get("success") and summ.get("summary"):
                ai_explain = summ["summary"].strip()
            else:
                logger.warning(
                    "AI report explanation unavailable: %s",
                    summ.get("error") or "empty response",
                )

            payload = {
                "success": True,
                "original_request": natural_language,
                "remote_host_context": host_context,
                "generated_command": command_to_run,
                "rag_retrieval": retrieved_examples,
                "results": execution_results,
                "natural_language_summary": formatted["natural_language_summary"],
                "formatted_report": formatted["formatted_report"],
                "ai_report_explanation": ai_explain,
                "intent_route_source": resolved.source,
                "execution_style_hint": resolved.execution_style,
            }
            if not ai_explain:
                payload["ai_report_explanation_error"] = (
                    "An AI explanation of the report could not be created. "
                    "Open the technical section below to see the full command output."
                )

            return jsonify(payload)

        except Exception as e:
            logger.error(f"Error in execute_command: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'Internal server error',
                'details': str(e),
                'natural_language_summary': format_error_summary(
                    'Something went wrong while handling your request',
                    details=str(e),
                ),
            }), 500

    @app.route('/api/servers', methods=['GET'])
    @login_required
    def get_servers():
        """Get list of available servers"""
        servers = app.config['REMOTE_SERVERS']
        return jsonify({'servers': servers})

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'llm_configured': bool(app.config['LLM_API_KEY']),
            'ssh_configured': bool(app.config['SSH_USER']),
            'servers_configured': len(app.config['REMOTE_SERVERS']) > 0
        })
