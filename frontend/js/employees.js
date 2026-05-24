/**
 * employees.js — Employee shift management and payroll summary.
 */

function employeesComponent() {
  return {
    shifts: [],
    payrollSummary: [],
    employees: [],
    activeTab: 'shifts',
    loading: false,
    showModal: false,
    modalLoading: false,
    form: {
      user_id: '', clock_in: '', clock_out: '',
      hourly_rate: 15, performance_rating: '', notes: '',
    },

    async init() {
      if (!Alpine.store('app').hasRole('admin', 'manager')) return;
      await Promise.all([this.loadShifts(), this.loadPayroll(), this.loadEmployees()]);
    },

    async loadShifts() {
      this.loading = true;
      try { this.shifts = await api.get('/api/employees/shifts', { limit: 50 }); } catch (e) { toast.error(e.message); } finally { this.loading = false; }
    },

    async loadPayroll() {
      try { this.payrollSummary = await api.get('/api/employees/payroll-summary'); } catch {}
    },

    async loadEmployees() {
      try {
        const users = await api.get('/api/users', { limit: 50 });
        this.employees = users.filter(u => ['cashier', 'manager', 'admin'].includes(u.role));
      } catch {}
    },

    openCreate() {
      const now = new Date();
      const toLocal = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      this.form = {
        user_id: '', clock_in: toLocal(now),
        clock_out: toLocal(new Date(now.getTime() + 8 * 3600000)),
        hourly_rate: 15, performance_rating: 4.0, notes: '',
      };
      this.showModal = true;
    },

    async saveShift() {
      if (!this.form.user_id || !this.form.clock_in) { toast.warning('Employee and clock-in time are required.'); return; }
      this.modalLoading = true;
      try {
        await api.post('/api/employees/shifts', {
          user_id: parseInt(this.form.user_id),
          clock_in: this.form.clock_in,
          clock_out: this.form.clock_out || null,
          hourly_rate: parseFloat(this.form.hourly_rate),
          performance_rating: this.form.performance_rating ? parseFloat(this.form.performance_rating) : null,
          notes: this.form.notes || null,
        });
        toast.success('Shift recorded!');
        this.showModal = false;
        await Promise.all([this.loadShifts(), this.loadPayroll()]);
      } catch (e) { toast.error(e.message); } finally { this.modalLoading = false; }
    },

    employeeName(userId) {
      const emp = this.employees.find(e => e.id === userId);
      return emp ? emp.name : `Employee #${userId}`;
    },

    ratingStars(rating) {
      if (!rating) return '—';
      const filled = Math.round(rating);
      return '★'.repeat(filled) + '☆'.repeat(5 - filled);
    },

    get totalPayroll() { return this.payrollSummary.reduce((s, e) => s + e.total_gross_pay, 0); },
    get totalHours() { return this.payrollSummary.reduce((s, e) => s + e.total_hours, 0); },
  };
}
