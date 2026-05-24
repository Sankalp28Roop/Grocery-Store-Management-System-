/**
 * products.js — Product catalog, inventory management, and barcode scanner.
 */

function productsComponent() {
  return {
    products: [],
    categories: [],
    loading: false,
    search: '',
    selectedCategory: '',
    lowStockOnly: false,
    viewMode: 'grid',  // 'grid' | 'table'
    showModal: false,
    editingProduct: null,
    modalLoading: false,

    form: {
      name: '', description: '', price: '', cost_price: '',
      stock_quantity: '', low_stock_threshold: '10',
      category: '', unit_of_measure: 'unit', image_url: '', barcode: '',
      bin_location: '', supplier_id: '',
    },

    // Barcode scanner
    barcodeInput: '',
    scannerActive: false,

    async init() {
      await Promise.all([this.loadProducts(), this.loadCategories()]);
      initScrollReveal();
    },

    async loadProducts() {
      this.loading = true;
      try {
        const params = { active_only: true };
        if (this.search) params.search = this.search;
        if (this.selectedCategory) params.category = this.selectedCategory;
        if (this.lowStockOnly) params.low_stock_only = true;
        this.products = await api.get('/api/products', params);
      } catch (e) {
        toast.error('Failed to load products: ' + e.message);
      } finally {
        this.loading = false;
        this.$nextTick(() => initScrollReveal());
      }
    },

    async loadCategories() {
      try {
        this.categories = await api.get('/api/products/categories');
      } catch {}
    },

    openCreate() {
      this.editingProduct = null;
      this.form = { name: '', description: '', price: '', cost_price: '', stock_quantity: '', low_stock_threshold: '10', category: '', unit_of_measure: 'unit', image_url: '', barcode: '', bin_location: '', supplier_id: '' };
      this.showModal = true;
    },

    openEdit(product) {
      this.editingProduct = product;
      this.form = {
        name: product.name, description: product.description || '',
        price: product.price, cost_price: product.cost_price,
        stock_quantity: product.stock_quantity, low_stock_threshold: product.low_stock_threshold,
        category: product.category || '', unit_of_measure: product.unit_of_measure,
        image_url: product.image_url || '', barcode: product.barcode || '',
        bin_location: product.bin_location || '', supplier_id: product.supplier_id || '',
      };
      this.showModal = true;
    },

    async saveProduct() {
      if (!this.form.name || !this.form.price) {
        toast.warning('Name and price are required.');
        return;
      }
      this.modalLoading = true;
      try {
        const payload = {
          ...this.form,
          price: parseFloat(this.form.price),
          cost_price: parseFloat(this.form.cost_price) || 0,
          stock_quantity: parseInt(this.form.stock_quantity) || 0,
          low_stock_threshold: parseInt(this.form.low_stock_threshold) || 10,
          supplier_id: this.form.supplier_id ? parseInt(this.form.supplier_id) : null,
        };
        if (this.editingProduct) {
          await api.put(`/api/products/${this.editingProduct.id}`, payload);
          toast.success('Product updated successfully!');
        } else {
          await api.post('/api/products', payload);
          toast.success('Product created successfully!');
        }
        this.showModal = false;
        await this.loadProducts();
      } catch (e) {
        toast.error(e.message);
      } finally {
        this.modalLoading = false;
      }
    },

    async deleteProduct(product) {
      if (!confirm(`Archive product "${product.name}"?`)) return;
      try {
        await api.delete(`/api/products/${product.id}`);
        toast.success('Product archived.');
        await this.loadProducts();
      } catch (e) {
        toast.error(e.message);
      }
    },

    async scanBarcode() {
      if (!this.barcodeInput.trim()) return;
      try {
        const product = await api.get(`/api/products/barcode/${this.barcodeInput.trim()}`);
        Alpine.store('app').addToCart(product);
        this.barcodeInput = '';
        toast.success(`Scanned: ${product.name} added to cart`);
      } catch (e) {
        toast.error(`Barcode not found: ${this.barcodeInput}`);
      }
    },

    stockStatusClass(product) {
      return fmt.stockStatus(product.stock_quantity, product.low_stock_threshold).css;
    },

    stockStatusLabel(product) {
      return fmt.stockStatus(product.stock_quantity, product.low_stock_threshold).label;
    },

    isExpiringSoon(product) {
      if (!product.expiry_date) return false;
      const days = (new Date(product.expiry_date) - Date.now()) / 86400000;
      return days > 0 && days <= 7;
    },

    get filteredProducts() { return this.products; },

    debouncedSearch: debounce(function() { this.loadProducts(); }, 350),
  };
}
