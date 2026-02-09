# Frequently Asked Questions and Glossary

## Getting Started

**Q: What is AWS Deadline Cloud?**

A: AWS Deadline Cloud is a fully managed service that simplifies render management for teams creating computer-generated 2D/3D graphics and visual effects for films, TV shows, commercials, games, industrial design, and more. With Deadline Cloud, you can set up, deploy, and scale rendering projects in minutes, so you can improve the efficiency of your rendering pipelines and take on more projects.

**Q: What is the submitter?**

A: The Cinema 4D submitter extension creates a button in Cinema 4D (Extensions > AWS Deadline Cloud Submitter) that allows you to access the submitter and submit jobs to Deadline Cloud. It automatically determines required files based on the loaded scene, allows you to specify render options, builds an Open Job Description template that defines the workflow, and submits the job to your chosen farm and queue.

**Q: What is the adaptor?**

A: The adaptor is a command-line Python-based application that enhances the functionality of Cinema 4D for running within a render farm like Deadline Cloud. Its primary purpose is to add a "sticky rendering" functionality where a single process instance of Cinema 4D is able to load the scene file and then dynamically be instructed to perform desired renders without needing to close and re-launch Cinema 4D between them. It also has additional benefits such as support for path mapping, and reporting the progress of your render to Deadline Cloud.

**Q: What is a job bundle?**

A: A job bundle is a directory structure that contains an Open Job Description (OpenJD) template, your Cinema 4D scene file path, paths to all assets (textures, models, etc.), and job-specific files required as input for your job. The submitter automatically creates this bundle and you can export it to review contents before submission or submit it using the Deadline Cloud CLI.

**Q: What are workers?**

A: Workers belong to fleets and run Deadline Cloud assigned tasks to complete steps and jobs. Workers store the logs from task operations in Amazon CloudWatch Logs. Workers can also use the job attachments feature to sync inputs and outputs to an Amazon Simple Storage Service (Amazon S3) bucket.

**Q: Do I need to know about AWS to use this?**

A: For Service Managed Fleets, you just need an AWS account to access the AWS Deadline Cloud dashboard and setup wizard, which makes it easier to create a cloud-based render farm. For Customer Managed Fleets, you'll need more AWS knowledge to manage your own fleet.

**Q: How much does it cost?**

A: You only pay for the compute time you use with pay-as-you-go pricing and Usage-Based Licensing (UBL). Costs vary based on instance types and render time. Built-in cost management capabilities include budget setting and usage tracking on a project-by-project basis, which gives you the ability to manage rendering costs and keep budgets on track. [Learn more about pricing](https://aws.amazon.com/deadline-cloud/pricing/).

## Technical Questions

**Q: What's the difference between Service-managed and Customer-managed fleets?**

A: **Service-managed** = A service-managed fleet (SMF) is a fleet of workers that have default settings provided by Deadline Cloud. These default settings are designed to be efficient and cost-effective.

**Customer-managed** = A customer-managed fleet (CMF) is a fleet of workers that you manage and that Deadline Cloud uses to process your jobs. We recommend using a CMF when you have existing on-premises workers to integrate with Deadline Cloud, workers in a co-located data center, or want direct control of Amazon EC2 workers. With a CMF, you have full control over and responsibility for the fleet, including provisioning, operations, management, and decommissioning workers.

**Q: What files get uploaded to Deadline Cloud?**

A: If you are using job attachments, your scene and all its assets are uploaded. Otherwise, it depends on your setup.

**Q: What are Job attachments?**

A: Job attachments enable you to transfer files back and forth between your workstation and AWS Deadline Cloud. With job attachments, you don't need to manually set up an Amazon S3 bucket for your files. Instead, when you create a queue with the Deadline Cloud console, you choose the bucket for your job attachments.

## Rendering Questions

**Q: Can I use Redshift?**

A: Yes! Redshift GPU rendering is supported.

**Q: How long do renders take?**

A: Cloud rendering can be much faster than local rendering because you can use multiple powerful instances simultaneously.

**Q: Why don't fonts work while submitting with macOS?**

A: Font functionality is currently only supported on Windows due to technical limitations. This is a known behavior in mixed macOS/Windows environments, as confirmed by Maxon's official documentation. 

For more information, see [Maxon's official FAQ on resolving missing fonts in Team Render](https://support.maxon.net/hc/en-us/articles/1500006439721-How-to-resolve-missing-fonts-in-Team-Render-for-Cinema-4D-install-fonts-or-make-Text-editable).

## Troubleshooting

**Q: My submitter button doesn't appear in Cinema 4D.**

A: Make sure you've installed the extension correctly and restarted Cinema 4D. Check the Console (Extensions > Console) for any error messages. Consider re-installing the submitter if the issue persists.

**Q: My render failed in the cloud.**

A: Common causes include missing assets, incorrect file paths, or insufficient memory. Check the job logs in the Deadline Cloud monitor.

**Q: Why are some of my textures or assets missing in the rendered output?**

A: This is typically a path mapping issue. Cinema 4D sometimes stores deep links (absolute paths) to assets in the scene file that cannot be edited. When the scene is submitted and rendered on the farm, it may still reference the original workstation paths even though the assets were uploaded.

**Workaround:** Enable "Save Cinema 4D Project with Assets" in the Job-Specific Settings tab of the submitter. This consolidates all assets into the project folder and fixes the paths before submission, ensuring they render correctly on the farm.

**Q: Can I cancel a job after submitting?**

A: Yes, you can cancel jobs through the Deadline Cloud monitor at any time.

**Q: Can I set job priorities?**

A: Yes, you can set job priority levels in the submitter to control render queue order, and you can adjust them later in the Deadline Cloud monitor!

**Q: What is automatic error checking?**

A: The submitter includes built-in error detection to catch common issues like missing assets before submission. This can be deactivated in the submitter.

**Q: How do I enable detailed logging for debugging rendering issues?**

A: The submitter includes an "Activate detailed logging" checkbox in the Job-Specific Settings that captures detailed logs for troubleshooting. When enabled:

1. The system automatically enables debug logging during rendering
2. After rendering completes, all logs are printed to the job output

To view the logs:
1. Open Deadline Cloud Monitor
2. Navigate to your completed job
3. Right-click on a task and select "View logs"
4. Enable the "View logs for all tasks" button
5. Scroll through the task run logs to find the "Shut down DetailedLogging" section for detailed logs

The logs are output in HTML format with timestamps. To save and view them in a web browser without timestamps:

```bash
cd deadline-cloud-for-cinema-4d/scripts
python clean_redshift_detailed_logs.py /path/to/detailed_logs.log
```

Or run without arguments and enter the path when prompted. This generates a `redshift_log_cleaned.html` file that's easier to read and compare.

Use detailed logging when you need to debug Redshift rendering issues, investigate rendering artifacts or errors, analyze renderer performance, or capture information for technical support.

**Q: I'm getting permission errors with a system-wide installation on Windows. How do I fix this?**

A: If users encounter permission errors when accessing the submitter after a system-wide installation:

1. **Verify initial setup was completed:**
   - Ensure Cinema 4D was opened as Administrator at least once
   - Ensure the dependency installation prompt was accepted
   - Check that the installation completed without errors

2. **Check file permissions:**
   - Navigate to the installation directory (e.g., `C:\Program Files\DeadlineCloudSubmitter\`)
   - Right-click → Properties → Security tab
   - Verify that "Users" group has "Read & execute" permissions
   - Permissions should be inherited by all subdirectories and files

3. **Manual permission fix (if needed):**
   - Open Command Prompt as Administrator
   - Run: `icacls "C:\Program Files\DeadlineCloudSubmitter" /grant *S-1-5-32-545:(OI)(CI)(RX) /T`
   - This grants read and execute permissions to all users

4. **Verify Cinema 4D Python environment:**
   - Open Cinema 4D as the affected user
   - Go to `Extensions` > `Console`
   - Try importing: `import deadline`
   - If this fails, the permissions may not be correctly applied

## Glossary

**Adaptor** - Software that runs on compute resources to execute your Cinema 4D renders or projects.

**Submitter** - The Cinema 4D extension that sends jobs to Deadline Cloud.

**Farm** - A farm is a where your project resources are located. It consists of queues and fleets.

**Queue** - A queue is where submitted jobs are located and scheduled to be rendered. A queue must be associated with a fleet to create a successful render. A queue can be associated with multiple fleets.

**Fleet** - A fleet is a group of worker nodes that do the rendering. Worker nodes process jobs. A fleet can be associated to multiple queues, and a queue can be associated to multiple fleets.

**Job** - A job is a rendering request. Users submit jobs. Jobs contain specific job properties that are outlined as steps and tasks.

**Steps** - Define the script to run on workers. Steps can have requirements such as minimum worker memory or other steps that need to complete first. Each step has one or more tasks.

**Tasks** - A unit of work sent to a worker to perform. A task is a combination of a step's script and parameters, such as a frame number, that are used in the script. The job is complete when all tasks are complete for all steps.

**Job attachments** - A job attachment is a Deadline Cloud feature that you can use to manage inputs and outputs for jobs. Job files are uploaded as job attachments during the rendering process. These files can be textures, 3D models, lighting rigs, and other similar items.

**Asset** - Files that your scene needs (textures, models, etc.).

**Take** - A render variation of the same scene.

**Priority** - The approximate order that Deadline Cloud processes a job in a queue. You can set the job priority between 0 and 100, jobs with a higher number priority are generally processed first. Jobs with the same priority are processed in the order received.
