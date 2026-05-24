/**
 * warehouse.js — Bin-level inventory and stock transfer management.
 */

function warehouseComponent() {
  return {
    inventory: [],
    transfers: [],
    bins: [],
    selectedBin: '',
    loading: false,
    showTransferModal: false,
    transferForm: { product_id: '', from_bin: '', to_bin: '', quantity: 1 },
    products: [],
    activeTab: 'inventory',

    async init() {
      if (!Alpine.store('app').hasRole('admin', 'manager')) return;
      await Promise.all([this.loadInventory(), this.loadBins(), this.loadTransfers()]);
    },

    async loadInventory() {
      this.loading = true;
      try {
        const params = {};
        if (this.selectedBin) params.bin_location = this.selectedBin;
        this.inventory = await api.get('/api/warehouse/inventory', params);
      } catch (e) { toast.error(e.message); } finally { this.loading = false; }
    },

    async loadBins() {
      try { this.bins = await api.get('/api/warehouse/bins'); } catch {}
    },

    async loadTransfers() {
      try { this.transfers = await api.get('/api/warehouse/transfers'); } catch {}
    },

    async loadProducts() {
      try { this.products = await api.get('/api/products'); } catch {}
    },

    openTransfer(item = null) {
      this.transferForm = {
        product_id: item ? item.product_id : '',
        from_bin: item ? item.bin_location : '',
        to_bin: '',
        quantity: 1,
      };
      this.$nextTick(async () => { if (!this.products.length) await this.loadProducts(); });
      this.showTransferModal = true;
    },

    async saveTransfer() {
      const { product_id, from_bin, to_bin, quantity } = this.transferForm;
      if (!product_id || !from_bin || !to_bin || !quantity) {
        toast.warning('All fields are required.'); return;
      }
      try {
        await api.post('/api/warehouse/transfer', {
          product_id: parseInt(product_id),
          from_bin,
          to_bin,
          quantity: parseInt(quantity),
        });
        toast.success(`Transferred ${quantity} unit(s) from ${from_bin} → ${to_bin}`);
        this.showTransferModal = false;
        await Promise.all([this.loadInventory(), this.loadTransfers(), this.loadBins()]);
      } catch (e) { toast.error(e.message); }
    },

    stockClass(item) {
      if (item.stock_quantity === 0) return 'critical';
      if (item.is_low_stock) return 'low-stock';
      return '';
    },

    get lowStockCount() { return this.inventory.filter(i => i.is_low_stock).length; },
    get outOfStockCount() { return this.inventory.filter(i => i.stock_quantity === 0).length; },
    get expiringCount() {
      return this.inventory.filter(i => {
        if (!i.expiry_date) return false;
        const days = (new Date(i.expiry_date) - Date.now()) / 86400000;
        return days > 0 && days <= 7;
      }).length;
    },
  };
}
