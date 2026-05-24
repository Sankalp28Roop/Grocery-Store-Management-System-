/**
 * pos.js — Point-of-Sale checkout flow component.
 */

function posComponent() {
  return {
    orders: [],
    loading: false,
    checkoutLoading: false,
    paymentMethod: 'cash',
    discount: 0,
    taxRate: 0.08,
    activeTab: 'cart',  // 'cart' | 'orders'
    invoiceOrder: null,
    showInvoice: false,
    invoiceData: null,

    async init() {
      await this.loadOrders();
    },

    async loadOrders() {
      this.loading = true;
      try {
        this.orders = await api.get('/api/orders', { limit: 30 });
      } catch (e) {
        toast.error(e.message);
      } finally {
        this.loading = false;
      }
    },

    async checkout() {
      const appStore = Alpine.store('app');
      if (appStore.cartItems.length === 0) {
        toast.warning('Cart is empty!');
        return;
      }
      this.checkoutLoading = true;
      try {
        const payload = {
          items: appStore.cartItems.map(i => ({
            product_id: i.product.id,
            quantity: i.quantity,
          })),
          payment_method: this.paymentMethod,
          discount_amount: parseFloat(this.discount) || 0,
          tax_rate: this.taxRate,
        };
        const order = await api.post('/api/orders/checkout', payload);
        appStore.clearCart();
        appStore.cartOpen = false;
        toast.success(`Order #${order.id} completed — ${fmt.currency(order.total_price)}`);
        await this.loadOrders();
        // Auto-show invoice
        await this.showOrderInvoice(order.id);
        this.activeTab = 'orders';
      } catch (e) {
        toast.error('Checkout failed: ' + e.message);
      } finally {
        this.checkoutLoading = false;
      }
    },

    async showOrderInvoice(orderId) {
      try {
        const data = await api.post(`/api/orders/${orderId}/invoice`, {});
        this.invoiceData = data;
        this.showInvoice = true;
      } catch (e) {
        toast.error('Could not generate invoice: ' + e.message);
      }
    },

    printInvoice() {
      window.print();
    },

    get subtotal() { return Alpine.store('app').cartSubtotal; },
    get taxAmount() { return this.subtotal * this.taxRate; },
    get discountAmount() { return Math.min(parseFloat(this.discount) || 0, this.subtotal); },
    get total() { return this.subtotal + this.taxAmount - this.discountAmount; },

    paymentOptions: [
      { value: 'cash', label: 'Cash', icon: '💵' },
      { value: 'card', label: 'Card', icon: '💳' },
      { value: 'digital_wallet', label: 'Wallet', icon: '📱' },
    ],

    orderStatusCss(status) { return fmt.orderStatusCss(status); },
  };
}
