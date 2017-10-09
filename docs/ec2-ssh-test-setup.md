# AWS SSH Server Setup

Basic instructions on how to set up an SSH server on an Ubuntu 16.04 EC2 instance.

## Step 1 — Create a New User

    sudo adduser testuser

## Step 2 — Create a Directory for File Transfers

    sudo mkdir -p /var/sftp/uploads
    sudo chown root:root /var/sftp
    sudo chmod 755 /var/sftp
    sudo chown testuser:testuser /var/sftp/uploads

## Step 3 — Restrict Access to One Directory

Open the SSH server configuration file

    sudo nano /etc/ssh/sshd_config

Add the following to the bottom of the file:

    Match User testuser
    ForceCommand internal-sftp
    PasswordAuthentication yes
    ChrootDirectory /var/sftp
    PermitTunnel no
    AllowAgentForwarding no
    AllowTcpForwarding no
    X11Forwarding no

Apply the configuration changes

    sudo systemctl restart sshd

# Step 4 — Verify the Configuration

Verify the user cannot via SSH

    ssh testuser@localhost

Verify the user can connect via SFTP

    sftp testuser@localhost
