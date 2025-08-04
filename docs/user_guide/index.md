# Render Cinema 4D with AWS Deadline Cloud

**User Guide & Getting Started**

This guide will walk you through everything you need to know about using AWS Deadline Cloud with Cinema 4D - from installation to your first successful render.

Transform your Cinema 4D rendering workflow with AWS Deadline Cloud - a fully managed service that scales your renders across hundreds of instances, freeing up your workstation for creative work.

## The Cinema 4D Submitter

![Cinema 4D Submitter Interface](images/submitter-dialog.png)

*The Deadline Cloud submitter integrates directly into Cinema 4D's Extensions menu.*

## Why Use Deadline Cloud for Cinema 4D?

<div class="benefit-tabs">
  <div class="carousel-container">
    <button class="carousel-arrow left" onclick="prevTab()">‹</button>
    <div class="tab-content-wrapper">
      <div class="tab-content active" id="tab-0">
        <h3>⚡ Scale Your Renders ⚡</h3>
        <p>Render complex scenes faster by distributing frames across multiple instances, reducing render times from hours to minutes.</p>
      </div>
      <div class="tab-content" id="tab-1">
        <h3>🖥️ Free Up Your Workstation 🖥️</h3>
        <p>Submit renders to Deadline Cloud and continue working on your next project while your scenes render in the background.</p>
      </div>
      <div class="tab-content" id="tab-2">
        <h3>💰 Pay Only for What You Use 💰</h3>
        <p>No upfront costs or long-term commitments. Pay only for the compute time you actually use.</p>
      </div>
      <div class="tab-content" id="tab-3">
        <h3>🎨 Redshift Ready 🎨</h3>
        <p>Full support for Maxon Cinema 4D and Maxon Redshift.</p>
      </div>
    </div>
    <button class="carousel-arrow right" onclick="nextTab()">›</button>
  </div>
</div>

## Supported Versions

- **Cinema 4D 2024 - 2025**
- **Redshift** (optional)
- **Windows and macOS** for job submission

## Get Started in 4 Simple Steps

**[Check the requirements first before proceeding!](getting-started.md#what-youll-need)**

Follow our step-by-step user guide to start rendering with Deadline Cloud in minutes.

*Click below to learn more about each step.*

<div class="grid cards" markdown>

-   📥 **[1. Install the Submitter](getting-started.md#step-1-install-the-submitter-5-minutes)**

    ---

    Add the Deadline Cloud extension to your Cinema 4D workstation

-   ☁️ **[2. Submit Your Scene](getting-started.md#step-2-submit-your-first-render-2-minutes)**

    ---

    Click the submit button to send your render to Deadline Cloud

-   📊 **[3. Monitor Progress](getting-started.md#step-3-monitor-your-renders)**

    ---

    Track your renders in real-time with the Deadline Cloud monitor

-   📤 **[4. Download Results](getting-started.md#step-4-download-your-results)**

    ---

    Completed frames become available for download when jobs succeed

</div>

<script>
let currentTab = 0;
let tabInterval;

function showTab(index) {
  const tabs = document.querySelectorAll('.tab-content');
  
  if (tabs.length === 0) return;
  
  // Hide current tab
  tabs[currentTab].classList.remove('active');
  
  // Show new tab
  currentTab = index;
  tabs[currentTab].classList.add('active');
  
  // Reset auto-advance when user clicks
  resetAutoAdvance();
}

function nextTab() {
  const nextIndex = (currentTab + 1) % 4;
  showTab(nextIndex);
}

function prevTab() {
  const prevIndex = (currentTab - 1 + 4) % 4;
  showTab(prevIndex);
}

function autoAdvance() {
  const nextTab = (currentTab + 1) % 4;
  showTabSilent(nextTab);
}

function showTabSilent(index) {
  const tabs = document.querySelectorAll('.tab-content');
  
  if (tabs.length === 0) return;
  
  tabs[currentTab].classList.remove('active');
  
  currentTab = index;
  tabs[currentTab].classList.add('active');
}

function resetAutoAdvance() {
  clearInterval(tabInterval);
  tabInterval = setInterval(autoAdvance, 4000);
}

// Initialize auto-advance
document.addEventListener('DOMContentLoaded', function() {
  tabInterval = setInterval(autoAdvance, 4000);
});
</script>

---

<div style="height: 100px;"></div>