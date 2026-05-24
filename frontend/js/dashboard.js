/**
 * dashboard.js — Admin dashboard KPI loading and metric display.
 */

function dashboardComponent() {
  return {
    metrics: null,
    loading: true,
    topProducts: [],
    lowStockItems: [],
    recentOrders: [],

    async init() {
      if (Alpine.store('app').hasRole('customer')) {
        this.loading = false;
        return;
      }
      await this.loadAll();
      initScrollReveal();
    },

    async loadAll() {
      this.loading = true;
      try {
        const [metrics, top, orders] = await Promise.all([
          api.get('/api/reports/dashboard'),
          api.get('/api/reports/top-products', { limit: 5 }),
          api.get('/api/orders', { limit: 8 }),
        ]);
        this.metrics = metrics;
        this.topProducts = top;
        this.recentOrders = orders;

        // Low stock
        const prods = await api.get('/api/products', { low_stock_only: true, limit: 10 });
        this.lowStockItems = prods;
      } catch (e) {
        toast.error('Failed to load dashboard: ' + e.message);
      } finally {
        this.loading = false;
        this.$nextTick(() => initScrollReveal());
      }
    },

    get metricCards() {
      if (!this.metrics) return [];
      return [
        {
          label: 'Today\'s Revenue',
          value: fmt.currency(this.metrics.revenue_today),
          icon: '💰',
          bg: 'var(--c-success-light)',
          color: '#1a8c35',
          delta: '+12.4%',
          deltaDir: 'up',
        },
        {
          label: 'Monthly Revenue',
          value: fmt.currency(this.metrics.revenue_this_month),
          icon: '📈',
          bg: 'var(--c-info-light)',
          color: 'var(--c-info)',
          delta: '+8.1%',
          deltaDir: 'up',
        },
        {
          label: 'Orders Today',
          value: fmt.number(this.metrics.total_orders_today),
          icon: '🛒',
          bg: 'var(--c-brand-light)',
          color: 'var(--c-brand)',
          delta: 'Live',
          deltaDir: '',
        },
        {
          label: 'Total Products',
          value: fmt.number(this.metrics.total_products),
          icon: '📦',
          bg: '#f5f0ff',
          color: '#7b3fe4',
          delta: `${this.metrics.low_stock_count} low stock`,
          deltaDir: this.metrics.low_stock_count > 0 ? 'down' : 'up',
        },
        {
          label: 'Active Customers',
          value: fmt.number(this.metrics.total_customers),
          icon: '👥',
          bg: '#fff4ec',
          color: '#d05a00',
          delta: '+24 this week',
          deltaDir: 'up',
        },
        {
          label: 'Low Stock Alerts',
          value: fmt.number(this.metrics.low_stock_count),
          icon: '⚠️',
          bg: 'var(--c-warning-light)',
          color: 'var(--c-warning)',
          delta: 'Needs attention',
          deltaDir: this.metrics.low_stock_count > 0 ? 'down' : '',
        },
        {
          label: 'Pending POs',
          value: fmt.number(this.metrics.pending_purchase_orders),
          icon: '📋',
          bg: 'var(--c-bg)',
          color: 'var(--c-text-secondary)',
          delta: 'Awaiting receipt',
          deltaDir: '',
        },
        {
          label: 'Expiring Soon',
          value: fmt.number(this.metrics.expiring_soon_count),
          icon: '📅',
          bg: 'var(--c-danger-light)',
          color: 'var(--c-danger)',
          delta: 'Within 7 days',
          deltaDir: this.metrics.expiring_soon_count > 0 ? 'down' : '',
        },
      ];
    },
  };
}
