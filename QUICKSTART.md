# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Environment

Copy the example environment file:
```bash
cp env.example .env
```

Edit `.env` and set at minimum:
- `SECRET_KEY`: Generate a random secret key (you can use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `LLM_API_KEY`: Your OpenAI API key (or compatible API)
- `SSH_USER`: Your SSH username
- `REMOTE_SERVERS`: Comma-separated list of servers (e.g., `server1.com,server2.com`)

## 3. Set Up SSH Access

Ensure you have SSH key-based authentication set up:
```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy to remote servers
ssh-copy-id user@server1.com
ssh-copy-id user@server2.com
```

Update `SSH_KEY_PATH` in `.env` if your key is in a non-standard location.

## 4. Run the Application

```bash
python run.py
```

Or:
```bash
python app.py
```

## 5. Access the Application

Open your browser and navigate to:
```
http://localhost:5001
```

## 6. Login

Default credentials:
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Change this password immediately after first login!**

## 7. Test the System

Try these example commands:
- "Show active connections on the server"
- "Check if 192.168.1.1 is alive"
- "Show disk storage usage"
- "Display network interfaces"

## Troubleshooting

### LLM API Issues
- Verify your API key is correct
- Check that `LLM_API_BASE_URL` is correct for your provider
- Ensure you have API credits/quota

### SSH Connection Issues
- Verify SSH key path is correct
- Test SSH connection manually: `ssh user@server`
- Check that SSH agent is running if using agent authentication
- Ensure remote servers are accessible

### Database Issues
- Delete `shellsentry.db` and restart to recreate database
- Check file permissions

### Port Already in Use
- Change port in `app.py` or `run.py`
- Or kill the process using port 5001

## Security Checklist

- [ ] Changed default admin password
- [ ] Set strong `SECRET_KEY`
- [ ] Configured SSH key authentication
- [ ] Reviewed command whitelist/blacklist
- [ ] Set `ALLOW_ROOT_EXECUTION=false` unless needed
- [ ] Configured firewall rules
- [ ] Set up HTTPS in production
- [ ] Regular security updates

