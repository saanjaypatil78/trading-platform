
# Node.js Setup Guide (Windows)

To fix the frontend dependency errors, you need to install Node.js and run `npm install`.

## Option 1: Installer (Recommended)
1. Go to the official website: [https://nodejs.org/](https://nodejs.org/)
2. Download the **LTS (Long Term Support)** version for Windows.
3. Run the installer (`.msi` file).
   - Accept the defaults.
   - **Important**: Ensure the box "Add to PATH" is checked (it usually is by default).

## Option 2: Using Winget (Command Line)
If you have Windows 10/11, you can install via terminal:
```powershell
winget install OpenJS.NodeJS.LTS
```

## Verify Installation
After installing, **restart your terminal/VS Code** completely to pick up the new PATH.
Run these commands to verify:
```powershell
node --version
npm --version
```

## Fix Frontend Dependencies
Once verified, run the following commands in this terminal:
```powershell
cd frontend/web
npm install
```
This will download all required libraries (`react`, `lucide-react`, etc.) and fix the IDE errors.
