// ============================================
// CONFIGURATION & CONSTANTS
// ============================================
const API_BASE = '/api';
const ENDPOINTS = {
  templates: `${API_BASE}/templates`,
  template: (name) => `${API_BASE}/template/${encodeURIComponent(name)}`,
  generate: `${API_BASE}/generate`,
  variations: `${API_BASE}/generate/variations`,
  statistics: `${API_BASE}/statistics`,
  history: `${API_BASE}/history`,
  validate: `${API_BASE}/validate`,
  costEstimate: `${API_BASE}/cost-estimate`
};

// ============================================
// UTILITY FUNCTIONS
// ============================================
class Utils {
  /**
   * Wrapper for fetch with JSON parsing and error handling.
   * @param {string} endpoint - API endpoint
   * @param {RequestInit} [options] - Fetch options
   * @returns {Promise<any>} - Parsed JSON response
   */
  static async fetchAPI(endpoint, options = {}) {
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    };

    try {
      const response = await fetch(endpoint, config);
      const data = await Utils.safeJson(response);

      if (!response.ok) {
        const message = data?.error || data?.message || 'Request failed';
        throw new Error(message);
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  /**
   * Safely parse JSON responses.
   * @param {Response} response
   * @returns {Promise<any>}
   */
  static async safeJson(response) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  /**
   * Display toast notification.
   * @param {string} message
   * @param {'success'|'error'|'info'|'warning'} [type]
   */
  static showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    const icons = {
      success: 'fa-check-circle',
      error: 'fa-exclamation-circle',
      info: 'fa-info-circle',
      warning: 'fa-exclamation-triangle'
    };
    const colors = {
      success: 'bg-green-500',
      error: 'bg-red-500',
      info: 'bg-blue-500',
      warning: 'bg-yellow-500'
    };

    toast.className = `${colors[type]} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3 transform transition-all duration-300 fade-in`;
    toast.setAttribute('role', 'status');
    toast.innerHTML = `
      <i class="fas ${icons[type]} text-lg"></i>
      <span class="flex-1">${message}</span>
      <button class="hover:bg-white/20 rounded p-1" aria-label="Close notification">
        <i class="fas fa-times"></i>
      </button>
    `;

    toast.querySelector('button')?.addEventListener('click', () => toast.remove());
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.transform = 'translateX(400px)';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  /**
   * Show or hide the loading overlay.
   * @param {boolean} show
   */
  static showLoading(show = true) {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    overlay.classList.toggle('hidden', !show);
  }

  /**
   * Format cost as currency with 6 decimals.
   * @param {number} cost
   * @returns {string}
   */
  static formatCost(cost) {
    const value = Number.isFinite(cost) ? cost : 0;
    return `$${value.toFixed(6)}`;
  }

  /**
   * Format numbers with locale separators.
   * @param {number} num
   * @returns {string}
   */
  static formatNumber(num) {
    return Number(num || 0).toLocaleString();
  }

  /**
   * Copy text to clipboard with feedback.
   * @param {string} text
   */
  static async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      Utils.showToast('Copied to clipboard!', 'success');
    } catch (err) {
      console.error('Clipboard error:', err);
      Utils.showToast('Failed to copy', 'error');
    }
  }

  /**
   * Download content as a text file.
   * @param {string} content
   * @param {string} filename
   */
  static downloadAsFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Debounce helper.
   * @param {Function} func
   * @param {number} wait
   * @returns {Function}
   */
  static debounce(func, wait = 300) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  }

  /**
   * Safely get an element by id.
   * @param {string} id
   * @returns {HTMLElement|null}
   */
  static el(id) {
    return document.getElementById(id);
  }
}

// ============================================
// TEMPLATE MANAGER
// ============================================
class TemplateManager {
  constructor() {
    this.templates = [];
    this.currentTemplate = null;
  }

  /**
   * Load all templates from API and populate UI.
   */
  async loadTemplates() {
    try {
      const data = await Utils.fetchAPI(ENDPOINTS.templates);
      this.templates = data.templates || [];
      this.populateTemplateSelect();
      this.populatePopularTemplates();
    } catch (error) {
      Utils.showToast(error.message || 'Failed to load templates', 'error');
    }
  }

  /**
   * Populate template dropdown.
   */
  populateTemplateSelect() {
    const select = Utils.el('templateSelect');
    if (!select) return;
    select.innerHTML = '<option value="">Choose a content type...</option>';

    this.templates.forEach((template) => {
      const option = document.createElement('option');
      option.value = template.name;
      option.textContent = `${template.name.replace(/_/g, ' ').toUpperCase()} - ${template.category}`;
      option.dataset.description = template.description || '';
      option.dataset.category = template.category || '';
      option.dataset.vars = JSON.stringify(template.required_variables || []);
      select.appendChild(option);
    });
  }

  /**
   * Populate quick template shortcuts.
   */
  populatePopularTemplates() {
    const container = Utils.el('popularTemplates');
    if (!container) return;
    const popular = this.templates.slice(0, 5);

    container.innerHTML = popular
      .map((template) => `
        <button class="quick-template w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm" data-template="${template.name}">
          ${template.name.replace(/_/g, ' ')}
        </button>
      `)
      .join('');
  }

  /**
   * Handle template selection.
   * @param {string} templateName
   */
  async selectTemplate(templateName) {
    if (!templateName) {
      this.resetTemplateSelection();
      return;
    }

    try {
      // Fetch template details from API
      const response = await fetch(`/api/template/${encodeURIComponent(templateName)}`);
      
      if (!response.ok) {
        throw new Error('Failed to load template');
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Template not found');
      }
      
      this.currentTemplate = data.template;
      
      // Update UI
      const select = Utils.el('templateSelect');
      if (select) select.value = templateName;
      
      this.showTemplateDescription();
      this.generateVariableInputs();
      this.enableActions();
      
      // Estimate cost if contentGenerator exists
      if (typeof contentGenerator !== 'undefined' && contentGenerator.estimateCost) {
        await contentGenerator.estimateCost();
      }
      
    } catch (error) {
      console.error('Template selection error:', error);
      Utils.showToast('Failed to load template: ' + error.message, 'error');
      this.disableActions();
    }
  }

  /**
   * Show template description and category.
   */
  showTemplateDescription() {
    const descDiv = Utils.el('templateDescription');
    const descText = Utils.el('templateDescriptionText');
    const category = Utils.el('templateCategory');
    if (!descDiv || !descText || !category || !this.currentTemplate) return;

    descText.textContent = this.currentTemplate.description || '';
    category.textContent = this.currentTemplate.category || '';
    descDiv.classList.remove('hidden');
  }

  /**
   * Create variable inputs dynamically.
   */
  generateVariableInputs() {
    const container = Utils.el('variablesContainer');
    if (!container || !this.currentTemplate) return;

    const requiredVars = this.currentTemplate.required_variables || [];
    const optionalVars = this.currentTemplate.optional_variables || {};

    if (requiredVars.length === 0 && Object.keys(optionalVars).length === 0) {
      container.innerHTML = `
        <div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <p class="text-sm text-center text-gray-700 dark:text-gray-300">
            <i class="fas fa-check-circle text-green-600 mr-2"></i>
            No variables required for this template
          </p>
        </div>
      `;
      // Enable buttons even with no variables
      this.enableActions();
      return;
    }

    const inputs = [];

    requiredVars.forEach((varName) => {
      inputs.push(this.createInput(varName, true));
    });

    Object.entries(optionalVars).forEach(([varName, defaultValue]) => {
      inputs.push(this.createInput(varName, false, defaultValue));
    });

    container.innerHTML = inputs.join('');

    // Attach listeners for cost estimation
    container.querySelectorAll('textarea, input').forEach((input) => {
      input.addEventListener('input', Utils.debounce(() => contentGenerator.estimateCost(), 400));
    });
  }

  /**
   * Create a single input block.
   * @param {string} name
   * @param {boolean} required
   * @param {string} [defaultValue]
   * @returns {string}
   */
  createInput(name, required, defaultValue = '') {
    const label = name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    return `
      <div class="space-y-2">
        <label class="block text-sm font-semibold text-gray-800 dark:text-gray-200">
          ${label}${required ? ' <span class="text-red-500">*</span>' : ''}
        </label>
        <textarea
          id="var_${name}"
          name="${name}"
          rows="2"
          class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary focus:border-transparent"
          placeholder="Enter ${label.toLowerCase()}..."
          ${required ? 'required' : ''}
        >${defaultValue || ''}</textarea>
      </div>
    `;
  }

  /**
   * Collect variables from inputs.
   * @returns {Record<string, string>}
   */
  getVariables() {
    const container = Utils.el('variablesContainer');
    if (!container) return {};

    const variables = {};
    container.querySelectorAll('textarea, input').forEach((input) => {
      if (input.value.trim()) {
        variables[input.name] = input.value.trim();
      }
    });
    return variables;
  }

  /**
   * Reset UI when no template is selected.
   */
  resetTemplateSelection() {
    this.currentTemplate = null;
    const container = Utils.el('variablesContainer');
    if (container) {
      container.innerHTML = `
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <i class="fas fa-arrow-up text-3xl mb-3 opacity-50"></i>
          <p>Select a template above to configure variables</p>
        </div>
      `;
    }
    const descDiv = Utils.el('templateDescription');
    if (descDiv) descDiv.classList.add('hidden');
    this.disableActions();
    const costBox = Utils.el('costEstimate');
    if (costBox) costBox.classList.add('hidden');
  }

  /**
   * Enable primary action buttons.
   */
  enableActions() {
    const generateBtn = Utils.el('generateBtn');
    const variationsBtn = Utils.el('variationsBtn');
    if (generateBtn) generateBtn.disabled = false;
    if (variationsBtn) variationsBtn.disabled = false;
  }

  /**
   * Disable primary action buttons.
   */
  disableActions() {
    const generateBtn = Utils.el('generateBtn');
    const variationsBtn = Utils.el('variationsBtn');
    if (generateBtn) generateBtn.disabled = true;
    if (variationsBtn) variationsBtn.disabled = true;
  }
}

// ============================================
// CONTENT GENERATOR
// ============================================
class ContentGenerator {
  constructor(templateManager) {
    this.templateManager = templateManager;
    this.lastResult = null;
  }

  /**
   * Validate form before API call.
   */
  validateForm() {
    const template = Utils.el('templateSelect')?.value;
    if (!template) throw new Error('Please select a template');

    const variables = this.templateManager.getVariables();
    const requiredCount = this.templateManager.currentTemplate?.required_variables?.length || 0;
    if (Object.keys(variables).length < requiredCount) {
      throw new Error('Please fill in all required fields');
    }
    return { template, variables };
  }

  /**
   * Estimate cost for current inputs.
   */
  async estimateCost() {
    const { template, variables } = (() => {
      const t = Utils.el('templateSelect')?.value;
      return { template: t, variables: this.templateManager.getVariables() };
    })();

    if (!template || Object.keys(variables).length === 0) {
      const box = Utils.el('costEstimate');
      if (box) box.classList.add('hidden');
      return;
    }

    try {
      const data = await Utils.fetchAPI(ENDPOINTS.costEstimate, {
        method: 'POST',
        body: JSON.stringify({ template, variables })
      });
      if (data.success && data.estimate) {
        const estimated = Utils.el('estimatedCost');
        if (estimated) estimated.textContent = Utils.formatCost(data.estimate.estimated_cost || 0);
        const box = Utils.el('costEstimate');
        if (box) box.classList.remove('hidden');
      }
    } catch (error) {
      console.warn('Cost estimate failed:', error);
    }
  }

  /**
   * Generate content via API.
   */
  async generate() {
    Utils.showLoading(true);
    try {
      const { template, variables } = this.validateForm();
      const useCache = !!Utils.el('useCache')?.checked;
      const temperature = parseFloat(Utils.el('temperature')?.value || '0.7');
      const maxTokens = parseInt(Utils.el('maxTokens')?.value || '500', 10);

      const payload = {
        template,
        variables,
        use_cache: useCache,
        temperature,
        max_tokens: maxTokens
      };

      const data = await Utils.fetchAPI(ENDPOINTS.generate, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (data.success && data.result) {
        this.lastResult = data.result;
        this.displayResult(data.result);
        await this.updateStatistics();
        Utils.showToast('Content generated successfully!', 'success');
      } else {
        throw new Error(data.error || 'Generation failed');
      }
    } catch (error) {
      Utils.showToast(error.message || 'Generation failed', 'error');
    } finally {
      Utils.showLoading(false);
    }
  }

  /**
   * Generate multiple variations.
   */
  async generateVariations() {
    Utils.showLoading(true);
    try {
      const { template, variables } = this.validateForm();
      const data = await Utils.fetchAPI(ENDPOINTS.variations, {
        method: 'POST',
        body: JSON.stringify({
          template,
          variables,
          count: 3,
          temperature_range: [0.5, 1.0]
        })
      });

      if (data.success && data.variations) {
        this.displayVariations(data.variations);
        await this.updateStatistics();
        Utils.showToast(`Generated ${data.variations.length} variations!`, 'success');
      } else {
        throw new Error(data.error || 'Failed to generate variations');
      }
    } catch (error) {
      Utils.showToast(error.message || 'Failed to generate variations', 'error');
    } finally {
      Utils.showLoading(false);
    }
  }

  /**
   * Render single result content and metadata.
   * @param {any} result
   */
  displayResult(result) {
    const section = Utils.el('outputSection');
    const content = Utils.el('outputContent');
    const metadata = Utils.el('outputMetadata');
    if (!section || !content || !metadata) return;

    content.textContent = result.content || 'No content generated.';

    const meta = [
      { label: 'Tokens', value: Utils.formatNumber(result.tokens_used?.total || 0), icon: 'fa-hashtag', color: 'text-blue-600 dark:text-blue-400' },
      { label: 'Cost', value: Utils.formatCost(result.cost || 0), icon: 'fa-dollar-sign', color: 'text-green-600 dark:text-green-400' },
      { label: 'Time', value: `${(result.generation_time || 0).toFixed(2)}s`, icon: 'fa-clock', color: 'text-purple-600 dark:text-purple-400' },
      { label: result.cached ? 'Cached' : 'Fresh', value: result.cached ? 'Yes' : 'No', icon: result.cached ? 'fa-bolt' : 'fa-globe', color: result.cached ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-600 dark:text-gray-400' }
    ];

    metadata.innerHTML = meta
      .map(
        (m) => `
        <div class="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg text-center">
          <i class="fas ${m.icon} ${m.color} mb-1"></i>
          <div class="text-xs text-gray-600 dark:text-gray-400">${m.label}</div>
          <div class="font-bold ${m.color}">${m.value}</div>
        </div>
      `
      )
      .join('');

    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /**
   * Render variations list.
   * @param {Array<any>} variations
   */
  displayVariations(variations) {
    const section = Utils.el('outputSection');
    const content = Utils.el('outputContent');
    const metadata = Utils.el('outputMetadata');
    if (!section || !content || !metadata) return;

    content.innerHTML = variations
      .map(
        (v, i) => `
        <div class="pb-6 ${i < variations.length - 1 ? 'border-b border-gray-200 dark:border-gray-700 mb-6' : ''}">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-bold text-lg text-primary">Variation ${i + 1}</h3>
            <span class="px-3 py-1 bg-secondary/10 text-secondary rounded-full text-xs font-semibold">temp: ${(v.variation_temperature || 0).toFixed(2)}</span>
          </div>
          <p class="text-gray-700 dark:text-gray-300 leading-relaxed">${v.content || 'No content'}</p>
        </div>
      `
      )
      .join('');

    metadata.innerHTML = '';
    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /**
   * Refresh statistics panel.
   */
  async updateStatistics() {
    try {
      const data = await Utils.fetchAPI(ENDPOINTS.statistics);
      const stats = data.stats || {};
      Utils.el('statGenerations')?.replaceChildren(document.createTextNode(Utils.formatNumber(stats.total_generations || 0)));
      Utils.el('statCost')?.replaceChildren(document.createTextNode(Utils.formatCost(stats.total_cost || 0)));
      Utils.el('statCacheRate')?.replaceChildren(document.createTextNode(`${((stats.cache_hit_rate || 0) * 100).toFixed(0)}%`));
      Utils.el('statAvgTime')?.replaceChildren(document.createTextNode(`${(stats.average_generation_time || 0).toFixed(1)}s`));
    } catch (error) {
      console.error('Failed to update statistics:', error);
    }
  }
}

// ============================================
// DARK MODE MANAGER
// ============================================
class DarkModeManager {
  constructor() {
    this.applyPreference();
    this.initToggle();
  }

  /**
   * Apply dark mode based on stored or system preference.
   */
  applyPreference() {
    const saved = localStorage.getItem('darkMode');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const enable = saved === 'enabled' || (saved === null && systemPrefersDark);
    document.documentElement.classList.toggle('dark', enable);
  }

  /**
   * Initialize toggle button.
   */
  initToggle() {
    const toggle = Utils.el('darkModeToggle');
    if (!toggle) return;
    toggle.addEventListener('click', () => {
      const isDark = document.documentElement.classList.toggle('dark');
      localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
    });
  }
}

// ============================================
// EVENT HANDLERS
// ============================================
function setupEventHandlers(templateManager, contentGenerator) {
  // Template selection
  Utils.el('templateSelect')?.addEventListener('change', (e) => {
    const value = e.target.value;
    templateManager.selectTemplate(value);
  });

  // Quick templates
  document.addEventListener('click', (e) => {
    const target = e.target.closest('.quick-template');
    if (target) {
      const templateName = target.dataset.template;
      const select = Utils.el('templateSelect');
      if (select) {
        select.value = templateName;
        select.dispatchEvent(new Event('change'));
      }
    }
  });

  // Generate form
  Utils.el('generatorForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    contentGenerator.generate();
  });

  // Variations button
  Utils.el('variationsBtn')?.addEventListener('click', () => {
    contentGenerator.generateVariations();
  });

  // Temperature slider
  Utils.el('temperature')?.addEventListener('input', (e) => {
    const value = e.target.value;
    const display = Utils.el('temperatureValue');
    if (display) display.textContent = value;
  });

  // Copy
  Utils.el('copyBtn')?.addEventListener('click', () => {
    const content = Utils.el('outputContent')?.textContent || '';
    Utils.copyToClipboard(content);
  });

  // Download
  Utils.el('downloadBtn')?.addEventListener('click', () => {
    const content = Utils.el('outputContent')?.textContent || '';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    Utils.downloadAsFile(content, `ai-content-${timestamp}.txt`);
  });

  // Refresh stats
  Utils.el('refreshStatsBtn')?.addEventListener('click', () => {
    contentGenerator.updateStatistics();
  });
}

// ============================================
// INITIALIZATION
// ============================================
let templateManager;
let contentGenerator;
let darkModeManager;

document.addEventListener('DOMContentLoaded', async () => {
  templateManager = new TemplateManager();
  contentGenerator = new ContentGenerator(templateManager);
  darkModeManager = new DarkModeManager();

  setupEventHandlers(templateManager, contentGenerator);

  await templateManager.loadTemplates();
  await contentGenerator.updateStatistics();
});
