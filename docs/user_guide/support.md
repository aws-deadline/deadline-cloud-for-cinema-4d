# Getting Support

Need help with the Cinema 4D Deadline Cloud submitter? This page will guide you through troubleshooting steps and how to get support when you need it.

## Before You Contact Support

Before reaching out for help, try these troubleshooting steps. They often resolve common issues and will help you provide better information if you do need to contact support.

### Troubleshooting Checklist

- **✅ Render one frame locally** - Before submitting to the cloud, render at least one frame locally in Cinema 4D to verify your scene renders correctly. This helps identify scene-specific issues vs. cloud rendering issues.

- **✅ Update to the latest submitter** - We release updates frequently with bug fixes and improvements. Your issue may already be fixed in a newer version. To check if you're running the latest version:
    - Find your current version: The version is displayed in the submitter window title
    - Compare with the latest release: Visit the [releases page](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/releases) to see the most recent version
    - If your version is older, update the submitter and test again before reporting the issue

- **✅ Check your Job-Specific Settings** - Review the Job-Specific Settings tab in the submitter. In particular, enable the **"Save Cinema 4D Project with Assets"** checkbox. This creates a temporary copy of your project with all assets and fixes file paths, helping identify missing files and organizing assets for render farms. [Learn more about this feature](submitter-features.md#job-specific-settings).

- **✅ Try different Cinema 4D versions** - If you're experiencing issues, test with Cinema 4D 2024, 2025, or 2026 to see if the problem is version-specific.

- **✅ Check existing GitHub issues** - Search the [GitHub Issues page](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues?q=is%3Aissue) to see if someone else has already reported your problem and found a solution.

- **✅ Try a different fleet operating system** - Submit your job to both Windows and Linux fleets if available. Windows generally has better support and compatibility for Cinema 4D features.

- **✅ Review session logs** - Download and review the session logs from Deadline Cloud Monitor. These logs often contain error messages that generally pinpoint the issue.

- **✅ Create a scene project file** - Use Cinema 4D's **File > Save Project with Assets** to create a self-contained project that includes all dependencies. Zip this file for easy sharing with support.

## When to Contact Support

Different types of issues should be directed to different support channels:

### AWS General Support

Contact AWS Support for:
- AWS account issues
- Billing questions
- General AWS service questions
- Deadline Cloud internal server errors in Deadline Cloud Monitor or while using CLI

You can also report Cinema 4D submitter/adaptor issues through AWS Support, but note that these requests may take longer as they need to be routed to the maintainers of this repository. For faster response on Cinema 4D-specific issues, we recommend using GitHub Issues (see below).

[Contact AWS Support](https://aws.amazon.com/contact-us/)

### Cinema 4D Submitter/Adaptor Support

**Use GitHub Issues as your primary channel** for Cinema 4D-specific problems:

- Submitter bugs or crashes
- Adaptor issues
- Rendering failures specific to Cinema 4D
- Feature requests
- Integration problems

[Open a GitHub Issue](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues)

## How to Report Issues on GitHub

### Bug Reports

**Before creating a new bug report:**

1. [Search existing bugs](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues?q=label%3Abug) to see if your problem has already been reported or fixed in latest versions.
2. If you find an existing issue that matches your problem:
   - Add a 👍 reaction to help us prioritize
   - Comment with any additional details or reproduction steps you can provide
   - This helps us understand how many users are affected

**If no existing issue matches**, [create a new bug report](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/new?template=bug.yml) using our bug report template. The template will guide you through providing all the necessary information.

### Feature Requests

**Before creating a new feature request:**

1. [Search existing enhancements](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues?q=is%3Aopen+label%3Aenhancement) to see if someone has already suggested your idea
2. If you find an existing request that matches:
   - Add a 👍 reaction to show your support
   - Comment with your specific use case - this strengthens the request and helps us understand different needs
   - The more users who express interest, the higher priority it receives

**If no existing request matches**, [create a new feature request](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/issues/new?template=feature_request.yml) using our feature request template. The template will guide you through providing all the necessary information.

**Note:** Feature requests help us prioritize development, but there's no guarantee of implementation timeline.

## What to Include in Your Support Request

### Required Information Checklist

When contacting support or creating a GitHub issue, always include:

- **Cinema 4D version** - e.g., Cinema 4D 2025.1.0
- **Operating System** - e.g., Windows 11, macOS 14.2
- **Submitter version** - Copy the entire contents of the About panel (Extensions > AWS Deadline Cloud Submitter > About)
- **Renderer** - Standard, Redshift, Arnold, etc.
- **Fleet configuration** - Worker OS (Windows/Linux), memory requirements, disk space, GPU type if using Redshift
- **Error messages** - Complete error text, not paraphrased

### How to Gather Log Files

Logs are essential for diagnosing issues. Here's how to collect them:

#### Enable Detailed Logging

1. In the Cinema 4D submitter, check **"Activate detailed logging"** in Job-Specific Settings
2. Submit your job
3. After the job completes (or fails), retrieve the logs:
   - Open Deadline Cloud Monitor
   - Navigate to your job
   - Click **"Download logs"** and select **"Entire session"** to download the full session logs for sharing with support

### How to Create Scene Project Files

A scene project file packages your Cinema 4D scene with all its assets:

1. **First, remove any confidential assets or data** from your scene before saving
2. In Cinema 4D, go to **File > Save Project with Assets**
3. Choose a destination folder
4. Cinema 4D will copy your scene and all referenced assets to this folder
5. Zip the entire project folder
6. Share the zip file with support

**Important:** Remove confidential assets *before* using "Save Project with Assets" - not after. Removing assets after saving can cause missing file errors that make it harder to diagnose your original issue.

**Tip:** The best way to share a reproducible test case is with a publicly available scene or a simplified scene that demonstrates the issue without confidential material. If you can recreate the problem with non-proprietary assets, this makes it much easier for support to investigate.

---

**Still need help?** Don't hesitate to reach out. The community and support team are here to help you succeed with Deadline Cloud!

[← Back to User Guide](index.md)
