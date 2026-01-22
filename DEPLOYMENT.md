
# Deployment Guide: Antigravity Trading Platform

## 1. Local Setup (Immediate Step)
**Yes, the `.msi` file you downloaded is exactly what you need.**
1.  **Run the `node-v24.13.0-x64.msi` installer.**
2.  Follow the prompts (Next -> Next -> Install).
3.  **Restart your computer** (or at least VS Code) after installation.
4.  Open the terminal in VS Code and run `frontend/web/npm install`.

---

## 2. Deployment Architecture (Production)
You want to deploy to **Vercel**. Here is the reality check for a Trading Platform:

### Frontend (Next.js) -> **Vercel (Recommended)**
*   **Why**: Vercel is built for Next.js. It handles the UI, static pages, and standard API routes perfectly.
*   **How**: Connect your GitHub repo to Vercel, point it to the `frontend/web` directory.

### Backend (Python/FastAPI) -> **NOT Vercel**
*   **Why Not**:
    *   **WebSockets**: Your app uses real-time market data (WebSockets). Vercel Serverless functions typically have a 10-60 second timeout and don't support persistent WebSocket connections.
    *   **Background Tasks**: The "Scanner" and "Backtesting" engines take time (minutes) and use background workers (Celery). Serverless functions will kill these processes before they finish.
    *   **State**: The architecture relies on Redis/RabbitMQ/Database which need persistent connections.
*   **Recommendation**: Host the Backend on **Render**, **Railway**, **DigitalOcean App Platform**, or a **VPS** (AWS EC2/Hetzner).

### The "Hybrid" Solution (Best Practice)
1.  **Deploy Frontend** to **Vercel**.
2.  **Deploy Backend** to **Render** (or Railway).
3.  **Connect them**: Set the `NEXT_PUBLIC_API_URL` environment variable in Vercel to point to your Render Backend URL.

---

## 3. Step-by-Step Deployment Plan


### Step 1: Choose ONE Backend Option
You only need **ONE** backend. Choose the option that fits your needs:

#### Option A: Render.com (Easiest)
*   **Pros**: Zero configuration, easy setup.
*   **Cons**: Free service spins down after inactivity (slow starts).
1.  Push your code to GitHub.
2.  Create a "Web Service" on Render.
3.  **Build Command**: `pip install -r requirements.txt`
4.  **Start Command**: `python launcher.py`
5.  **Env Vars**: Add keys from your `.env` file.

#### Option B: AWS EC2 Free Tier (Best for Control)
**WARNING**: Free Tier (t2.micro) only has **1GB RAM**.
**Solution**: Use the "Lite" setup (`docker-compose.ec2-free.yml`).

**Free Tier Safety Checklist:**
*   [ ] **Elastic IP**: Release if not in use.
*   [ ] **EBS Volume**: Keep total storage under 30GB.
*   [ ] **Data Transfer**: Stay under 100GB/month.

1.  **Launch EC2 Instance**: Ubuntu 22.04 LTS, t2.micro or t3.micro.
2.  **Setup Swap** (CRITICAL - prevents crashes):
    ```bash
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    ```
3.  **Install Docker**:
    ```bash
    sudo apt update
    sudo apt install docker.io docker-compose -y
    sudo usermod -aG docker $USER
    # Log out and log back in for permissions to take effect
    ```
4.  **Deploy**:
    ```bash
    git clone https://github.com/YOUR_REPO/trading-platform.git
    cd trading-platform
    docker-compose -f docker-compose.ec2-free.yml up -d
    ```

### Step 2: Deploy Frontend (on Vercel)
1.  Go to Vercel Dashboard -> "Add New Project".
2.  Import your GitHub Repository.
3.  **Root Directory**: `frontend/web`.
4.  **Environment Variables**:
    *   `NEXT_PUBLIC_API_URL`:
        *   If using **Option A**: `https://your-app.onrender.com`
        *   If using **Option B**: `http://YOUR_EC2_IP:8000`
5.  Click **Deploy**.

---

## FAQ: Why not Vercel for Backend?
**Q: Why can't I deploy the Python Backend to Vercel?**
A: Vercel is designed for **Serverless Functions** (short-lived, instant tasks). Your Trading Backend requires:
1.  **WebSockets**: Real-time market data requires a connection that stays open forever. Vercel kills connections after ~10-60 seconds.
2.  **Long-Running Tasks**: A generic backtest or AI scan might take 5 minutes. Vercel will timeout before it finishes.
3.  **Background Workers**: Features like "Scheduled Scans" need a process running 24/7. Serverless functions only run when a user visits the site.

**Summary**: Vercel is perfect for the *VisuaI Interface* (Frontend), but you need a *Real Server* (VPS/Render) for the *Brain* (Backend).

