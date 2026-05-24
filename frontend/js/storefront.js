/**
 * storefront.js — Alpine.js controller for B2C Customer Storefront.
 * Modeled after the high-end Grocery Mania v2 theme.
 */

function storefrontComponent() {
  return {
    loading: false,
    products: [],
    categories: [],
    selectedCategory: '',
    searchQuery: '',
    sortBy: 'default', // 'default' | 'price-asc' | 'price-desc' | 'rating-desc'
    
    // Quick View Modal
    selectedProduct: null,
    quickViewQty: 1,
    
    // Newsletter
    newsletterEmail: '',
    
    // Hero Slider
    activeSlide: 0,
    sliderInterval: null,
    slides: [],
    promos: [],
    info: {
      newsletter: { title: '', description: '' },
      footer: {
        about_title: '',
        about_text: '',
        hours_title: '',
        hours: [],
        support_title: '',
        support: []
      }
    },

    async init() {
      await this.loadStorefrontConfig();
      this.startSlider();
      await Promise.all([this.loadProducts(), this.loadCategories()]);
    },

    async loadStorefrontConfig() {
      this.loading = true;
      try {
        const config = await api.get('/api/storefront/config');
        this.slides = config.hero || [];
        this.promos = config.promos || [];
        this.info = config.info || {
          newsletter: { title: '', description: '' },
          footer: { about_title: '', about_text: '', hours_title: '', hours: [], support_title: '', support: [] }
        };
      } catch (e) {
        toast.error('Failed to load storefront configuration: ' + e.message);
      } finally {
        this.loading = false;
      }
    },

    async loadProducts() {
      this.loading = true;
      try {
        const params = { active_only: true };
        if (this.selectedCategory) params.category = this.selectedCategory;
        if (this.searchQuery) params.search = this.searchQuery;
        
        let fetched = await api.get('/api/products', params);
        
        // Sorting Logic
        if (this.sortBy === 'price-asc') {
          fetched.sort((a, b) => a.price - b.price);
        } else if (this.sortBy === 'price-desc') {
          fetched.sort((a, b) => b.price - a.price);
        }
        
        this.products = fetched;
      } catch (e) {
        toast.error('Failed to load shop items: ' + e.message);
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

    selectCategory(cat) {
      this.selectedCategory = (this.selectedCategory === cat) ? '' : cat;
      this.loadProducts();
    },

    triggerSearch() {
      this.loadProducts();
    },

    // Hero Slider functions
    startSlider() {
      this.sliderInterval = setInterval(() => {
        this.activeSlide = (this.activeSlide + 1) % this.slides.length;
      }, 5000);
    },

    stopSlider() {
      if (this.sliderInterval) {
        clearInterval(this.sliderInterval);
      }
    },

    nextSlide() {
      this.stopSlider();
      this.activeSlide = (this.activeSlide + 1) % this.slides.length;
      this.startSlider();
    },

    prevSlide() {
      this.stopSlider();
      this.activeSlide = (this.activeSlide - 1 + this.slides.length) % this.slides.length;
      this.startSlider();
    },

    // Quick view
    openQuickView(product) {
      this.selectedProduct = product;
      this.quickViewQty = 1;
    },

    closeQuickView() {
      this.selectedProduct = null;
    },

    increaseQty() {
      this.quickViewQty++;
    },

    decreaseQty() {
      if (this.quickViewQty > 1) {
        this.quickViewQty--;
      }
    },

    addSelectedToCart() {
      if (!this.selectedProduct) return;
      Alpine.store('app').addToCart(this.selectedProduct, this.quickViewQty);
      this.closeQuickView();
    },

    // Newsletter Signup Mockup
    subscribeNewsletter() {
      if (!this.newsletterEmail.trim() || !this.newsletterEmail.includes('@')) {
        toast.warning('Please enter a valid email address.');
        return;
      }
      toast.success('Thank you! You have successfully signed up for our newsletter. 🥬');
      this.newsletterEmail = '';
    },

    stockStatusClass(product) {
      return fmt.stockStatus(product.stock_quantity, product.low_stock_threshold).css;
    },

    stockStatusLabel(product) {
      return fmt.stockStatus(product.stock_quantity, product.low_stock_threshold).label;
    }
  };
}
