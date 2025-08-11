# Frequently Asked Questions and Glossary

## Getting Started

**Q: What is AWS Deadline Cloud?**  
A: AWS Deadline Cloud is a fully managed service that simplifies render management for teams creating computer-generated 2D/3D graphics and visual effects for films, TV shows, commercials, games, and industrial design. With Deadline Cloud, you can set up, deploy, and scale rendering projects in minutes, so you can improve the efficiency of your rendering pipelines and take on more projects.

**Q: What is the submitter?**  
A: The submitter is a Cinema 4D extension that adds a button to your Extensions menu. It automatically detects your scene assets, packages everything into a job bundle, and submits your render to AWS Deadline Cloud. It handles all the technical complexity so you can focus on your creative work.

**Q: What is the adaptor?**  
A: The adaptor runs on cloud workers and acts as a bridge between Deadline Cloud and Cinema 4D. It launches Cinema 4D, loads your scene, and executes renders. It provides "sticky rendering" - keeping Cinema 4D open between frames instead of restarting, which speeds up rendering significantly.

**Q: What is a job bundle?**  
A: A job bundle is a package containing your Cinema 4D scene file, all assets (textures, models, etc.), render settings, and workflow instructions. The submitter automatically creates this bundle and you can export it to review contents before submission.

**Q: What is a worker?**  
A: A worker is a cloud computer that renders your frames. Workers automatically scale up when you have jobs and scale down when idle to minimize costs. They can use CPU-only rendering or include GPUs for faster rendering.

**Q: Do I need to know about AWS to use this?**  
A: No! The submitter handles all the technical AWS details. You just need an AWS account and the Cinema 4D extension.

**Q: How much does it cost?**  
A: You only pay for the compute time you use on AWS. Costs vary based on instance types and render time. [Learn more about pricing](https://aws.amazon.com/deadline-cloud/pricing/).

## Technical Questions

**Q: What's the difference between Service Managed and Customer Managed fleets?**  
A: **Service Managed** = AWS handles everything for you. Cinema 4D and licensing are automatically available, and everything is ready to go. Just submit your job and start rendering. This is recommended for most users.

**Customer Managed** = You set up and manage your own render computers. You install Cinema 4D yourself, handle licensing, and maintain the systems. Choose this only if you have specific technical requirements or existing infrastructure.

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
