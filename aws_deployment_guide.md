# ☁️ AWS Free Tier Deployment Guide

To deploy the **Reddit Insights Engine** for free without crashing the 1GB RAM limits of the AWS `t2.micro` Free Tier, we use a Linux Swap File to act as virtual memory for our PyTorch AI models.

## Phase 1: Launching the EC2 Instance

1. Log in to your [AWS Management Console](https://aws.amazon.com/console/) and head to **EC2**.
2. Click **Launch Instance**.
3. **Name:** `reddit-insights-server`
4. **OS Image (AMI):** Select **Ubuntu 24.04 LTS** (or 22.04 LTS). Make sure it says "Free tier eligible".
5. **Instance Type:** `t2.micro` (1 vCPU, 1 GiB Memory).
6. **Key Pair:** Click "Create new key pair", name it `reddit-key`, download the `.pem` file, and keep it safe.
7. **Network Settings:** 
   * Check **Allow SSH traffic**
   * Check **Allow HTTP traffic from the internet** (crucial for our React app)
8. **Storage:** Increase it to `25 GB` (Free tier allows up to 30GB). We need space for Docker containers and the AI models.
9. Click **Launch Instance**.

## Phase 2: Connecting to your Server

Once the instance says "Running", select it and click the **Connect** button at the top. You can use **EC2 Instance Connect** (browser-based) for the easiest experience.

## Phase 3: The Magic Setup Script (Swap + Docker)

Since the `t2.micro` only has 1GB of RAM, downloading and loading the `Falconsai` Summarization model will trigger Linux's OOM (Out of Memory) Killer, crashing the server.

To fix this, we create a 4GB Virtual RAM file (Swap File). Inside your EC2 terminal, copy and paste this entire block at once:

```bash
# 1. Create a 4GB Swap File to prevent AI Out-Of-Memory crashes
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo cp /etc/fstab /etc/fstab.bak
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 2. Update the system and install Git
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install git -y

# 3. Install Docker and Docker-Compose
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. Install standard Docker-Compose (v1/v2 compatibility)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Phase 4: Deploying your App

Now that the server is robust, clone your repository and spin up the production containers.

```bash
# 1. Clone your GitHub repository
git clone https://github.com/joao-tinelli/reddit-insights-engine.git

# 2. Enter the folder
cd reddit-insights-engine

# 3. Build and launch the containers in detached mode
sudo docker-compose up --build -d
```

### 🚀 You're live!
Go back to the AWS Console, find the **Public IPv4 address** of your EC2 instance, and copy it into your browser (e.g., `http://54.123.45.67`).

*Note: The very first search you make on the live site will take ~10-20 seconds because the Backend container is downloading the 400MB T5 AI model into the `/app/tmp` persistent volume. After that, it will be cached forever!*

## Phase 5: Fixing a Custom Domain (Optional)

If you don't want to use the raw AWS IP address (e.g. `54.123.45.67`), you can easily connect a real domain name (like `reddit-engine.com`).

1. **Buy a Domain name**: Go to a registrar like Namecheap, GoDaddy, or Hostinger and purchase your desired `.com`.
2. **Link the IP via DNS**:
   * Open your domain's DNS Management Panel in your registrar.
   * Add an **A Record**.
   * Set the Host/Name to `@` (which stands for the root domain).
   * Set the Value/IP to your **AWS Public IPv4 Address**.
3. **Wait for propagation**: DNS can take anywhere from 5 minutes to 24 hours to update globally across the world.
4. **Access your site**: You can now access your app directly via `http://yourdomain.com/`.

*(Note: To enable the green padlock `https://`, you would need to install Let's Encrypt / Certbot SSL certificates on your Nginx container).*
