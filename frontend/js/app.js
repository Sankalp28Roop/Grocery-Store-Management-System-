/**
 * app.js — Alpine.js global store, client-side router, and page orchestration.
 */

document.addEventListener('alpine:init', () => {
  // Synchronously restore user session to avoid timing race conditions on page refresh
  const savedToken = localStorage.getItem('gsm_token');
  const savedUser = storage.get('gsm_user');
  if (savedToken) {
    api.setToken(savedToken);
  }

  Alpine.store('app', {
    // Auth state
    isAuthenticated: !!(savedToken && savedUser),
    currentUser: savedUser || null,
    token: savedToken || null,

    // UI state
    activePage: (savedUser && savedUser.role === 'customer') ? 'storefront' : 'dashboard',
    sidebarOpen: false,
    loading: false,
    notificationCount: 0,
    notifications: [],
    showNotifPanel: false,

    // Cart state
    cartOpen: false,
    cartItems: [],  // { product, quantity }

    // Chatbot state
    chatOpen: false,
    chatMessages: [],

    // ── Init ────────────────────────────────────────────────────────
    async init() {
      if (this.isAuthenticated) {
        await this.loadNotifications();
      }
      // Restore cart from session
      const savedCart = storage.get('gsm_cart', []);
      this.cartItems = savedCart;
    },

    // ── Auth ─────────────────────────────────────────────────────────
    async login(email, password) {
      const data = await api.post('/api/auth/login', { email, password });
      this.token = data.access_token;
      api.setToken(data.access_token);
      const user = await api.get(`/api/users/${data.user_id}`);
      this.currentUser = user;
      storage.set('gsm_user', user);
      this.isAuthenticated = true;
      this.activePage = (user.role === 'customer') ? 'storefront' : 'dashboard';
      toast.success(`Welcome back, ${user.name.split(' ')[0]}! 👋`);
      await this.loadNotifications();
    },

    logout() {
      this.isAuthenticated = false;
      this.currentUser = null;
      this.token = null;
      this.cartItems = [];
      this.chatMessages = [];
      api.setToken(null);
      storage.remove('gsm_user');
      storage.remove('gsm_cart');
      this.activePage = 'dashboard';
      toast.info('Signed out successfully.');
    },

    // ── Navigation ────────────────────────────────────────────────────
    navigate(page) {
      this.activePage = page;
      this.sidebarOpen = false;
      // Trigger scroll reveal on new content
      setTimeout(() => {
        document.querySelectorAll('.reveal').forEach(el => {
          el.classList.remove('visible');
        });
        initScrollReveal();
      }, 100);
    },

    hasRole(...roles) {
      return this.currentUser && roles.includes(this.currentUser.role);
    },

    // ── Cart ──────────────────────────────────────────────────────────
    addToCart(product, qty = 1) {
      const existing = this.cartItems.find(i => i.product.id === product.id);
      if (existing) {
        existing.quantity += qty;
      } else {
        this.cartItems.push({ product, quantity: qty });
      }
      this.saveCart();
      toast.success(`${product.name} added to cart`);
    },

    removeFromCart(productId) {
      this.cartItems = this.cartItems.filter(i => i.product.id !== productId);
      this.saveCart();
    },

    updateCartQty(productId, delta) {
      const item = this.cartItems.find(i => i.product.id === productId);
      if (!item) return;
      item.quantity = Math.max(1, item.quantity + delta);
      this.saveCart();
    },

    clearCart() { this.cartItems = []; this.saveCart(); },
    saveCart() { storage.set('gsm_cart', this.cartItems); },

    get cartCount() { return this.cartItems.reduce((s, i) => s + i.quantity, 0); },
    get cartSubtotal() { return this.cartItems.reduce((s, i) => s + i.product.price * i.quantity, 0); },
    get cartTax() { return this.cartSubtotal * 0.08; },
    get cartTotal() { return this.cartSubtotal + this.cartTax; },

    // ── Notifications ────────────────────────────────────────────────
    async loadNotifications() {
      try {
        const data = await api.get('/api/reports/notifications', { unread_only: true });
        this.notifications = data.slice(0, 10);
        this.notificationCount = data.filter(n => !n.is_read).length;
      } catch (e) {
        // Silently fail — non-critical
      }
    },

    async markRead(id) {
      await api.patch(`/api/reports/notifications/${id}/read`, {});
      const n = this.notifications.find(n => n.id === id);
      if (n) { n.is_read = true; this.notificationCount = Math.max(0, this.notificationCount - 1); }
    },
  });
});
