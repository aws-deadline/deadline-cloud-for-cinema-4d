# Frequently Asked Questions and Glossary

## Getting Started

**Q: What is AWS Deadline Cloud?**  
A: AWS Deadline Cloud is a fully managed service that simplifies render management for teams creating computer-generated 2D/3D graphics and visual effects for films, TV shows, commercials, games, and industrial design. With Deadline Cloud, you can set up, deploy, and scale rendering projects in minutes, so you can improve the efficiency of your rendering pipelines and take on more projects.

**Q: What is the submitter?**  
A: The Cinema 4D submitter extension creates a button in Cinema 4D (Extensions > AWS Deadline Cloud Submitter) that allows you to access the submitter and submit jobs to Deadline Cloud. It automatically determines required files based on the loaded scene, allows you to specify render options, builds an Open Job Description template that defines the workflow, and submits the job to your chosen farm and queue. 

**Q: What is the adaptor?**  
A: The adaptor application is a command-line Python-based application that enhances the functionality of Cinema 4D for running within a render farm like Deadline Cloud. 

**Q: What is a job bundle?**  
A: A job bundle is a directory structure that contains an Open Job Description (OpenJD) template, your Cinema 4D scene file, all assets (textures, models, etc.), and job-specific files required as input for your job. The submitter automatically creates this bundle and you can export it to review contents before submission or submit it using the Deadline Cloud CLI.

**Q: What is a worker?**  
A: A worker is a cloud computer that renders your frames. AWS Deadline Cloud lets you scale thousands of workers up and down minute-to-minute, allowing you to render complex assets, accelerate production timelines, take on new projects, and meet challenging turnaround times. Workers automatically scale down when you're done to minimize costs.

**Q: Do I need to know about AWS to use this?**  
A: No! The submitter handles all the technical AWS details. You just need an AWS account and the Cinema 4D extension.

**Q: How much does it cost?**  
A: You only pay for the compute time you use with pay-as-you-go pricing and Usage-Based Licensing (UBL). Costs vary based on instance types and render time. Built-in cost management capabilities include budget setting and usage tracking on a project-by-project basis, which gives you the ability to manage rendering costs and keep budgets on track. [Learn more about pricing](https://aws.amazon.com/deadline-cloud/pricing/).

## Technical Questions

**Q: What's the difference between Service Managed and Customer Managed fleets?**  
A: **Service Managed** = A service-managed fleet (SMF) is a fleet of workers that have default settings provided by Deadline Cloud. These default settings are designed to be efficient and cost-effective.

**Customer Managed** = A customer-managed fleet (CMF) is a fleet of workers that you manage and that Deadline Cloud uses to process your jobs. Use a CMF when you have existing on-premises workers to integrate with Deadline Cloud, workers in a co-located data center, or want direct control of Amazon EC2 workers. With a CMF, you have full control over and responsibility for the fleet, including provisioning, operations, management, and decommissioning workers.

**Q: What files get uploaded to Deadline Cloud?**  
A: The submitter automatically detects your scene file, textures, models, and other assets needed for rendering.

## Rendering Questions

**Q: Can I use Redshift?**  
A: Yes! Redshift GPU rendering is supported.

**Q: How long do renders take?**  
A: Cloud rendering can be much faster than local rendering because you can use multiple powerful instances simultaneously.

**Q: Where do my rendered images go?**  
A: Completed frames are available by downloading the outputs in the Deadline Cloud monitor.

## Troubleshooting

**Q: My submitter button doesn't appear in Cinema 4D**  
A: Make sure you've installed the extension correctly and restarted Cinema 4D. Check the Console for any error messages.

**Q: My render failed in the cloud**  
A: Common causes include missing assets, incorrect file paths, or insufficient memory. Check the job logs in the Deadline Cloud monitor.

**Q: Can I cancel a job after submitting?**  
A: Yes, you can cancel jobs through the Deadline Cloud monitor at any time.

**Q: Can I set job priorities?**  
A: Yes, you can set job priority levels in the submitter to control render queue order.

**Q: What is automatic error checking?**  
A: The submitter includes built-in error detection to catch common issues like missing assets before submission. This can be deactivated in the submitter.

## Glossary

**Adaptor** - Software that runs on cloud computers to execute your Cinema 4D renders  
**Submitter** - The Cinema 4D extension that sends jobs to Deadline Cloud  
**Farm** - Your rendering facility in the cloud  
**Queue** - Different rendering departments with specific settings  
**Fleet** - Group of computers that do the rendering  
**Job** - Your render request sent to the cloud  
**Asset** - Files your scene needs (textures, models, etc.)   
**Take** - Different render variations of the same scene

<br>
