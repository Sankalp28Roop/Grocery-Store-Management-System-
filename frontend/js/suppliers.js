/**
 * suppliers.js — Supplier management and Purchase Order workflow.
 */

function suppliersComponent() {
  return {
    suppliers: [],
    purchaseOrders: [],
    activeTab: 'suppliers',
    loading: false,
    showSupplierModal: false,
    showPOModal: false,
    editingSupplier: null,
    modalLoading: false,

    supplierForm: { name: '', contact_email: '', contact_phone: '', address: '', reliability_rating: 9.0, notes: '' },

    poForm: {
      supplier_id: '',
      notes: '',
      expected_delivery: '',
      items: [{ product_id: '', quantity: 1, unit_cost: 0 }],
    },

    products: [],

    async init() {
      if (!Alpine.store('app').hasRole('admin', 'manager')) return;
      await Promise.all([this.loadSuppliers(), this.loadPOs(), this.loadProducts()]);
    },

    async loadSuppliers() {
      this.loading = true;
      try { this.suppliers = await api.get('/api/suppliers'); } catch (e) { toast.error(e.message); } finally { this.loading = false; }
    },

    async loadPOs() {
      try { this.purchaseOrders = await api.get('/api/suppliers/purchase-orders'); } catch {}
    },

    async loadProducts() {
      try { this.products = await api.get('/api/products'); } catch {}
    },

    openCreateSupplier() {
      this.editingSupplier = null;
      this.supplierForm = { name: '', contact_email: '', contact_phone: '', address: '', reliability_rating: 9.0, notes: '' };
      this.showSupplierModal = true;
    },

    openEditSupplier(s) {
      this.editingSupplier = s;
      this.supplierForm = { name: s.name, contact_email: s.contact_email || '', contact_phone: s.contact_phone || '', address: s.address || '', reliability_rating: s.reliability_rating, notes: s.notes || '' };
      this.showSupplierModal = true;
    },

    async saveSupplier() {
      if (!this.supplierForm.name) { toast.warning('Supplier name is required.'); return; }
      this.modalLoading = true;
      try {
        if (this.editingSupplier) {
          await api.put(`/api/suppliers/${this.editingSupplier.id}`, this.supplierForm);
          toast.success('Supplier updated!');
        } else {
          await api.post('/api/suppliers', this.supplierForm);
          toast.success('Supplier created!');
        }
        this.showSupplierModal = false;
        await this.loadSuppliers();
      } catch (e) { toast.error(e.message); } finally { this.modalLoading = false; }
    },

    async deleteSupplier(s) {
      if (!confirm(`Delete supplier "${s.name}"?`)) return;
      try { await api.delete(`/api/suppliers/${s.id}`); toast.success('Supplier deleted.'); await this.loadSuppliers(); } catch (e) { toast.error(e.message); }
    },

    openCreatePO() {
      this.poForm = { supplier_id: '', notes: '', expected_delivery: '', items: [{ product_id: '', quantity: 1, unit_cost: 0 }] };
      this.showPOModal = true;
    },

    addPOItem() { this.poForm.items.push({ product_id: '', quantity: 1, unit_cost: 0 }); },
    removePOItem(idx) { if (this.poForm.items.length > 1) this.poForm.items.splice(idx, 1); },

    autofillCost(item) {
      const product = this.products.find(p => p.id === parseInt(item.product_id));
      if (product) item.unit_cost = product.cost_price || product.price * 0.6;
    },

    async savePO() {
      if (!this.poForm.supplier_id) { toast.warning('Please select a supplier.'); return; }
      this.modalLoading = true;
      try {
        const payload = {
          supplier_id: parseInt(this.poForm.supplier_id),
          notes: this.poForm.notes,
          expected_delivery: this.poForm.expected_delivery || null,
          items: this.poForm.items.filter(i => i.product_id).map(i => ({
            product_id: parseInt(i.product_id),
            quantity: parseInt(i.quantity),
            unit_cost: parseFloat(i.unit_cost),
          })),
        };
        await api.post('/api/suppliers/purchase-orders', payload);
        toast.success('Purchase Order created!');
        this.showPOModal = false;
        await this.loadPOs();
      } catch (e) { toast.error(e.message); } finally { this.modalLoading = false; }
    },

    async updatePOStatus(po, status) {
      try {
        await api.patch(`/api/suppliers/purchase-orders/${po.id}/status`, { status });
        toast.success(`PO #${po.id} marked as ${status}`);
        if (status === 'received') toast.info('Stock quantities updated automatically!');
        await this.loadPOs();
      } catch (e) { toast.error(e.message); }
    },

    poStatusCss(s) { return fmt.poStatusCss(s); },
  };
}
