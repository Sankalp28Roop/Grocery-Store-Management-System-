/**
 * chatbot.js — Integrated FreshMart AI assistant panel.
 */

function chatbotComponent() {
  return {
    messages: [
      { role: 'assistant', text: "👋 Hi! I'm your FreshMart assistant. Ask me about products, navigation, or grocery suggestions!" }
    ],
    inputText: '',
    loading: false,
    suggestions: [
      'Show me popular products',
      'What fruits do you have?',
      'How do I check inventory?',
      'Where are the sales reports?',
    ],

    async sendMessage(text) {
      const msg = text || this.inputText.trim();
      if (!msg) return;
      this.messages.push({ role: 'user', text: msg });
      this.inputText = '';
      this.loading = true;
      this.suggestions = [];
      this.scrollToBottom();

      try {
        const data = await api.post('/api/chatbot/message', { message: msg });
        this.messages.push({ role: 'assistant', text: data.reply, products: data.product_recommendations });
        if (data.suggestions.length) this.suggestions = data.suggestions;
      } catch (e) {
        this.messages.push({ role: 'assistant', text: `Sorry, I encountered an error: ${e.message}` });
      } finally {
        this.loading = false;
        this.scrollToBottom();
      }
    },

    handleKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.sendMessage(); }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = document.getElementById('chat-messages-list');
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    // Markdown-lite renderer for bold and newlines
    renderText(text) {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    },
  };
}
