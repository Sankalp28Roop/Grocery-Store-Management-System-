/**
 * reports.js — Analytics charts and sales data visualizations using Chart.js.
 */

function reportsComponent() {
  return {
    period: 'daily',
    daysBack: 30,
    salesData: [],
    topProducts: [],
    loading: false,
    charts: {},

    async init() {
      if (!Alpine.store('app').hasRole('admin', 'manager')) return;
      await this.loadData();
    },

    async loadData() {
      this.loading = true;
      try {
        const [sales, top] = await Promise.all([
          api.get('/api/reports/sales', { period: this.period, days_back: this.daysBack }),
          api.get('/api/reports/top-products', { limit: 10 }),
        ]);
        this.salesData = sales;
        this.topProducts = top;
        this.$nextTick(() => this.renderCharts());
      } catch (e) {
        toast.error('Failed to load reports: ' + e.message);
      } finally {
        this.loading = false;
      }
    },

    renderCharts() {
      this.destroyCharts();

      // Revenue & Profit Line Chart
      const revenueCtx = document.getElementById('revenueChart');
      if (revenueCtx && this.salesData.length > 0) {
        this.charts.revenue = new Chart(revenueCtx, {
          type: 'line',
          data: {
            labels: this.salesData.map(d => d.period),
            datasets: [
              {
                label: 'Revenue',
                data: this.salesData.map(d => d.revenue),
                borderColor: '#00a86b',
                backgroundColor: 'rgba(0,168,107,0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#00a86b',
                pointRadius: 4,
              },
              {
                label: 'Profit',
                data: this.salesData.map(d => d.profit),
                borderColor: '#007aff',
                backgroundColor: 'rgba(0,122,255,0.08)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#007aff',
                pointRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { position: 'top' },
              tooltip: {
                callbacks: {
                  label: ctx => `${ctx.dataset.label}: ${fmt.currency(ctx.parsed.y)}`,
                },
              },
            },
            scales: {
              y: {
                ticks: { callback: v => fmt.currency(v) },
                grid: { color: 'rgba(0,0,0,0.04)' },
              },
              x: { grid: { display: false } },
            },
          },
        });
      }

      // Orders Bar Chart
      const ordersCtx = document.getElementById('ordersChart');
      if (ordersCtx && this.salesData.length > 0) {
        this.charts.orders = new Chart(ordersCtx, {
          type: 'bar',
          data: {
            labels: this.salesData.map(d => d.period),
            datasets: [{
              label: 'Orders',
              data: this.salesData.map(d => d.order_count),
              backgroundColor: 'rgba(0,168,107,0.75)',
              borderRadius: 8,
              borderSkipped: false,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: { grid: { color: 'rgba(0,0,0,0.04)' } },
              x: { grid: { display: false } },
            },
          },
        });
      }

      // Top Products Doughnut Chart
      const topCtx = document.getElementById('topProductsChart');
      if (topCtx && this.topProducts.length > 0) {
        const top5 = this.topProducts.slice(0, 5);
        this.charts.topProducts = new Chart(topCtx, {
          type: 'doughnut',
          data: {
            labels: top5.map(p => p.name),
            datasets: [{
              data: top5.map(p => p.total_revenue),
              backgroundColor: ['#00a86b', '#007aff', '#ff9500', '#ff3b30', '#af52de'],
              borderWidth: 0,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
              legend: { position: 'right' },
              tooltip: {
                callbacks: {
                  label: ctx => `${ctx.label}: ${fmt.currency(ctx.parsed)}`,
                },
              },
            },
          },
        });
      }
    },

    destroyCharts() {
      Object.values(this.charts).forEach(c => c.destroy());
      this.charts = {};
    },

    get totalRevenue() { return this.salesData.reduce((s, d) => s + d.revenue, 0); },
    get totalProfit() { return this.salesData.reduce((s, d) => s + d.profit, 0); },
    get totalOrders() { return this.salesData.reduce((s, d) => s + d.order_count, 0); },
    get avgOrderValue() { return this.totalOrders ? this.totalRevenue / this.totalOrders : 0; },

    async changePeriod(p) {
      this.period = p;
      await this.loadData();
    },
  };
}
