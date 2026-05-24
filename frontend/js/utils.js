/**
 * utils.js — Shared API client, formatters, and validators.
 */

// ─── API Client ──────────────────────────────────────────────────────────────
const API_BASE = '';  // Same-origin since FastAPI serves both

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('gsm_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem('gsm_token', token);
    else localStorage.removeItem('gsm_token');
  }

  _headers(extra = {}) {
    const headers = { 'Content-Type': 'application/json', ...extra };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    return headers;
  }

  async request(method, path, body = null, opts = {}) {
    const url = `${API_BASE}${path}`;
    const config = {
      method,
      headers: this._headers(opts.headers || {}),
    };
    if (body !== null) config.body = JSON.stringify(body);
    try {
      const res = await fetch(url, config);
      if (res.status === 204) return null;
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data.detail || `HTTP ${res.status}`;
        throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join(', ') : msg);
      }
      return data;
    } catch (err) {
      if (err.name === 'TypeError') throw new Error('Network error — is the server running?');
      throw err;
    }
  }

  get(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request('GET', qs ? `${path}?${qs}` : path);
  }
  post(path, body)   { return this.request('POST', path, body); }
  put(path, body)    { return this.request('PUT', path, body); }
  patch(path, body)  { return this.request('PATCH', path, body); }
  delete(path)       { return this.request('DELETE', path); }
}

const api = new ApiClient();

// ─── Formatters ──────────────────────────────────────────────────────────────
const fmt = {
  currency: (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0),
  number: (n) => new Intl.NumberFormat('en-US').format(n || 0),
  percent: (n) => `${(n * 100).toFixed(1)}%`,
  date: (d) => d ? new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(d)) : '—',
  datetime: (d) => d ? new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(d)) : '—',
  relativeDate: (d) => {
    if (!d) return '—';
    const diff = Date.now() - new Date(d).getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return fmt.date(d);
  },
  initials: (name) => name ? name.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2) : '?',
  stockStatus: (qty, threshold) => {
    if (qty === 0) return { label: 'Out of Stock', css: 'badge-out-of-stock' };
    if (qty <= threshold) return { label: 'Low Stock', css: 'badge-low-stock' };
    return { label: 'In Stock', css: 'badge-in-stock' };
  },
  orderStatusCss: (status) => ({
    completed: 'status-completed',
    pending: 'status-pending',
    processing: 'status-processing',
    cancelled: 'status-cancelled',
    refunded: 'status-cancelled',
  }[status] || 'status-pending'),
  poStatusCss: (status) => ({
    draft: 'status-draft',
    sent: 'status-sent',
    received: 'status-received',
    cancelled: 'status-cancelled',
  }[status] || 'status-draft'),
  tierColor: (tier) => ({
    bronze: '#cd7f32', silver: '#aaa', gold: '#f5a623', platinum: '#6e6e73'
  }[tier] || '#aaa'),
  categoryEmoji: (cat) => ({
    'Fruits': '🍎', 'Vegetables': '🥦', 'Dairy': '🥛', 'Bakery': '🍞',
    'Seafood': '🐟', 'Snacks': '🍿', 'Beverages': '🥤', 'Meat': '🥩',
    'Frozen': '🧊', 'Pantry': '🫙', 'Organic': '🌿',
  }[cat] || '🛒'),
};

// ─── Toast Notifications ──────────────────────────────────────────────────────
class Toast {
  constructor() {
    this.container = null;
  }

  _init() {
    if (this.container) return;
    let el = document.getElementById('toast-container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast-container';
      el.style.cssText = `
        position: fixed; top: 1.5rem; right: 1.5rem; z-index: 9999;
        display: flex; flex-direction: column; gap: 0.625rem;
        pointer-events: none;
      `;
      document.body.appendChild(el);
    }
    this.container = el;
  }

  show(message, type = 'info', duration = 4000) {
    this._init();
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const colors = {
      success: '#34c759', error: '#ff3b30', warning: '#ff9500', info: '#007aff'
    };
    const toast = document.createElement('div');
    toast.style.cssText = `
      display: flex; align-items: center; gap: 0.75rem;
      background: #1c1c1e; color: white;
      padding: 0.875rem 1.25rem; border-radius: 14px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      font-size: 0.875rem; font-weight: 500;
      border-left: 3px solid ${colors[type]};
      pointer-events: all; cursor: pointer;
      animation: fadeSlideUp 0.25s ease both;
      max-width: 320px;
      font-family: Inter, sans-serif;
    `;
    toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
    toast.onclick = () => toast.remove();
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.animation = 'fadeSlideUp 0.2s ease reverse both';
      setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  success(msg) { this.show(msg, 'success'); }
  error(msg) { this.show(msg, 'error'); }
  warning(msg) { this.show(msg, 'warning'); }
  info(msg) { this.show(msg, 'info'); }
}

const toast = new Toast();

// ─── Scroll Reveal Observer ───────────────────────────────────────────────────
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  return observer;
}

// ─── Debounce ─────────────────────────────────────────────────────────────────
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ─── Local Storage Helpers ────────────────────────────────────────────────────
const storage = {
  get: (key, def = null) => {
    try { return JSON.parse(localStorage.getItem(key)) ?? def; } catch { return def; }
  },
  set: (key, val) => localStorage.setItem(key, JSON.stringify(val)),
  remove: (key) => localStorage.removeItem(key),
};
