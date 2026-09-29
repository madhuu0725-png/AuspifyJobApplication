// ==========================================================================
// JobPortal Client Interactions & Enhancements
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide Icons if loaded
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Auto-dismiss Flash Toasts after 4.5 seconds
  const toasts = document.querySelectorAll('.alert-toast');
  toasts.forEach(toast => {
    setTimeout(() => {
      toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 400);
    }, 4500);
  });

  // AJAX Job Save/Bookmark Toggle
  const saveButtons = document.querySelectorAll('.js-save-job-btn');
  saveButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const jobId = btn.dataset.jobId;
      if (!jobId) return;

      try {
        const response = await fetch(`/jobs/${jobId}/toggle-save`, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
          }
        });

        if (response.redirected) {
          window.location.href = response.url;
          return;
        }

        const data = await response.json();
        if (data.success) {
          const icon = btn.querySelector('i') || btn.querySelector('svg');
          if (data.saved) {
            btn.classList.add('active');
            if (icon) {
              icon.setAttribute('data-lucide', 'bookmark-check');
            }
          } else {
            btn.classList.remove('active');
            if (icon) {
              icon.setAttribute('data-lucide', 'bookmark');
            }
          }
          if (window.lucide) window.lucide.createIcons();
          showToast(data.message, 'info');
        }
      } catch (err) {
        console.error('Error toggling save job:', err);
      }
    });
  });

  // Modal Dialog System (Data attributes: data-modal-target, data-modal-close)
  const openModalBtns = document.querySelectorAll('[data-modal-target]');
  openModalBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-modal-target');
      const modal = document.querySelector(targetId);
      if (modal) {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
      }
    });
  });

  const closeModalBtns = document.querySelectorAll('[data-modal-close]');
  closeModalBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal-overlay');
      if (modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  });

  // Close modal when clicking on overlay backdrop
  const modals = document.querySelectorAll('.modal-overlay');
  modals.forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  });

  // Escape key closes modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const openModal = document.querySelector('.modal-overlay.open');
      if (openModal) {
        openModal.classList.remove('open');
        document.body.style.overflow = '';
      }
    }
  });

  // Tab System
  const tabContainers = document.querySelectorAll('.js-tabs-container');
  tabContainers.forEach(container => {
    const tabs = container.querySelectorAll('.tab-btn');
    const panes = container.querySelectorAll('.tab-pane');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tabTarget;
        tabs.forEach(t => t.classList.remove('active'));
        panes.forEach(p => p.style.display = 'none');

        tab.classList.add('active');
        const activePane = container.querySelector(target);
        if (activePane) activePane.style.display = 'block';
      });
    });
  });
});

// Dynamic In-page Toast Utility
function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `alert-toast ${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button type="button" class="toast-close" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}
