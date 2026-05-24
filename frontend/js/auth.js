/**
 * auth.js — Login and Registration form logic.
 */

function authComponent() {
  return {
    mode: 'login',   // 'login' | 'register'
    loading: false,
    error: null,

    // Login form
    loginEmail: 'sankalp.swarup@grocerymania.local',
    loginPassword: 'admin123',

    // Register form
    regName: '',
    regEmail: '',
    regPassword: '',
    regRole: 'customer',

    async login() {
      if (!this.loginEmail || !this.loginPassword) {
        this.error = 'Please enter your email and password.';
        return;
      }
      this.loading = true;
      this.error = null;
      try {
        await Alpine.store('app').login(this.loginEmail, this.loginPassword);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    async register() {
      if (!this.regName || !this.regEmail || !this.regPassword) {
        this.error = 'All fields are required.';
        return;
      }
      this.loading = true;
      this.error = null;
      try {
        await api.post('/api/auth/register', {
          name: this.regName,
          email: this.regEmail,
          password: this.regPassword,
          role: this.regRole,
        });
        toast.success('Account created! Please sign in.');
        this.mode = 'login';
        this.loginEmail = this.regEmail;
        this.loginPassword = '';
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },

    // Quick demo login shortcuts
    quickLogin(role) {
      const creds = {
        admin: { email: 'sankalp.swarup@grocerymania.local', password: 'admin123' },
        manager: { email: 'manager@freshmart.com', password: 'manager123' },
        cashier: { email: 'cashier@freshmart.com', password: 'cashier123' },
        customer: { email: 'emma@example.com', password: 'customer123' },
      };
      const c = creds[role];
      if (c) { this.loginEmail = c.email; this.loginPassword = c.password; }
    },
  };
}
