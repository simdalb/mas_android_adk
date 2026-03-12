# Android MAS Starter Project

This is the starter project for a multi-agent system (MAS) that will eventually autonomously build and maintain a Python-based Android app.

At this stage, this project gives you:

- the orchestration script  
- the agent definitions  
- settings and policy files  
- prompts  
- guardrails  
- tool placeholders  
- architecture documentation  
- this administrator HOW-TO  

---

# 1. What this project does right now

Right now it is a safe starter scaffold.

It does **not yet** fully build the Android app for you.  
It does **not yet** connect to real Google ADK calls.  
It does **not yet** implement the real Android framework adapter code.

What it does do:

- defines the agents  
- defines the workflows  
- defines the future import points  
- defines the safety rules  
- gives you the folder structure and setup path  

---

# 2. What you need to do now

You, as the administrator, mainly need to:

1. install the required software  
2. create the platform accounts  
3. keep credentials safe  
4. place approved configuration values into `.env` and `settings.yaml`  
5. approve internet access and releases when needed  

You should **not** need to write code.

---

# 3. Before you start

Create a working folder on your computer, for example:

`C:\android_mas_starter` on Windows

or

`/home/yourname/android_mas_starter` on Linux

Put all files from this starter project inside that folder.

---

# 4. Install the software

## 4.1 Install Python

Install Python 3.11 or newer.

After installation, verify it:

```bash
python --version
```

If that does not work, try:

```bash
python3 --version
```

---

## 4.2 Install Git

Install Git.

Verify:

```bash
git --version
```

---

## 4.3 Install Android Studio

Install Android Studio.

During setup, install:

- Android SDK  
- Android SDK Platform Tools  
- Android Emulator  
- at least one recent Android API image  

After installation:

1. Open Android Studio once  
2. Let it finish SDK setup  
3. Open Device Manager  
4. Create an emulator, for example `Pixel_6_API_34`

Write that emulator name into `settings.yaml`:

```yaml
android:
  avd_name: "Pixel_6_API_34"
```

---

## 4.4 Create a Python virtual environment

From the project folder:

```bash
python -m venv .venv
```

Activate it.

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Then install requirements:

```bash
pip install -r requirements.txt
```

---

# 5. Create your local secret file

Copy `.env.example` to `.env`.

On Windows:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Important:

- never send `.env` to anyone  
- never commit `.env` to git  
- never paste secret keys into chat unless absolutely necessary  
- keep backup copies securely in a password manager  

---

# 6. Set up Git for version control

Inside the project folder:

```bash
git init
git add .
git commit -m "Initial MAS starter scaffold"
```

If you want remote backup, create a private repository on GitHub, GitLab, or another provider.

Then connect it:

```bash
git remote add origin YOUR_PRIVATE_REPOSITORY_URL
git push -u origin main
```

Use a private repository, not a public one.

---

# 7. Accounts you will probably need

For the final app, you will likely need these accounts:

- Google account dedicated to the project  
- Firebase project  
- Google Play Console account  
- AdMob account  
- payment method / business details for Play Console if you sell subscriptions  

Use a separate project email account, not your main personal email, if possible.

Example:

```
yourappbusiness@example.com
```

This keeps the project cleaner and reduces personal risk.

---

# 8. Firebase setup HOW-TO

Firebase will likely be used for:

- authentication  
- cloud data storage  
- optional file storage  
- analytics only if you choose it later  

---

## 8.1 Create a Firebase project

Go to Firebase Console.

1. Click **Create project**  
2. Choose a project name  
3. Disable optional extras unless you really need them  
4. Finish setup  

---

## 8.2 Add an Android app to Firebase

Inside the Firebase project, choose **Add app**.

Select **Android**.

Enter your Android package name from `settings.yaml`, for example:

```yaml
android:
  package_name: "com.example.linknest"
```

Register the app.

Download `google-services.json` only when needed.

Do not commit that file to git.

---

## 8.3 Enable authentication methods

In Firebase Authentication:

Open **Sign-in method**

Enable the methods you want, likely:

- Email/Password  
- Google Sign-In  

Do not enable many methods unless necessary.

---

## 8.4 Firestore / Storage

If using Firestore:

- Create a Firestore database  
- Start with locked-down rules, not open test rules  
- Keep security strict from the beginning  

If using Storage:

- Enable Storage  
- Again, use strict rules  

---

## 8.5 Fill `.env`

Example fields:

```
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_WEB_API_KEY=your-web-api-key
FIREBASE_ANDROID_APP_ID=your-android-app-id
FIREBASE_STORAGE_BUCKET=your-bucket-name
```

---

# 9. Google Play Console HOW-TO

You need this only when you are closer to release.

## 9.1 Create the account

- Sign in with your project Google account  
- Register a Play Console developer account  
- Complete identity and payment details as required  

---

## 9.2 Create the app entry

1. Click **Create app**  
2. Choose app name  
3. Choose default language  
4. Mark whether it contains ads  
5. Save  

---

## 9.3 Internal testing first

Before any wider release:

- use internal testing  
- keep testing small and controlled  
- do not publish publicly until the app is reviewed properly  

---

## 9.4 Put relevant values in `.env`

```
GOOGLE_PLAY_PACKAGE_NAME=com.example.linknest
```

---

# 10. AdMob HOW-TO

Use AdMob only if you actually want the free ad-supported version.

## 10.1 Create AdMob account

- Sign in with project Google account  
- Create an AdMob account  
- Add your app when ready  

---

## 10.2 Create ad units

Create the ad unit types you want, for example:

- banner  
- interstitial  

Then put IDs into `.env`:

```
ADMOB_APP_ID=...
ADMOB_BANNER_AD_UNIT_ID=...
ADMOB_INTERSTITIAL_AD_UNIT_ID=...
```

Important:

- use test ads during development  
- never click your own live ads  
- do not release ad logic before policy review  

---

# 11. Password and key handling HOW-TO

## Rules you should follow

- use a password manager  
- use unique passwords for every platform  
- enable two-factor authentication where possible  
- do not store secrets in README files  
- do not store secrets in source code  
- do not email secrets in plain text  
- do not commit private keys to git  

---

## Recommended approach

Store secrets in:

- `.env` locally  
- a secure password manager  
- optionally a secure secrets vault later  

For Android signing keys:

- create them only when needed  
- store them outside the project folder if possible  
- keep backup copies in a safe place  
- never commit them to git  

---

# 12. Running the starter project

From the project folder:

```bash
python mas_android_adk.py
```

That runs in dry-run mode by default.

For a non-dry run:

```bash
python mas_android_adk.py --real-run
```

At this stage, non-dry-run is still mostly placeholder behavior, so start with dry-run.

---

# 13. Files you will edit

You will usually only edit:

### `settings.yaml`

This controls:

- selected framework  
- app package name  
- emulator name  
- iteration settings  
- monetization flags  

### `.env`

This stores:

- API keys  
- project IDs  
- ad IDs  
- package name  
- future credentials  

You should rarely need to edit Python files yourself.

---

# 14. Safe operating rules for you

You should:

- keep the repository private  
- use a separate project Google account  
- keep backups  
- review release packets before approving release  
- approve internet access only when the reason is clear  

You should **not**:

- paste secrets into public places  
- use public git repositories for this project  
- approve unclear internet requests  
- approve release unless tests and security notes are acceptable  

---

# 15. Suggested app names

Possible names:

- LinkNest  
- MediaHarbor  
- VaultLinks  
- StreamShelf  
- SaveMyMedia  

You can change the name later.

---

# 16. What comes next

The next development step should be:

- real Google ADK integration  
- framework adapter scaffolding  
- actual Android app repository layout  
- instrumentation-test command flows  
- Firebase rules and admin HOW-TO documents  
- release packet generation  

---

# 17. Summary

Your main responsibilities are:

- install tools  
- create accounts  
- keep credentials safe  
- fill `.env`  
- fill `settings.yaml`  
- approve releases and internet requests  

The system is intended to do the rest.