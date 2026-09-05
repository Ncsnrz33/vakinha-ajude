/**
 * Vakinha Clone - Main Interactive Controller & Campaign Configuration
 */

// ==========================================================================
// 1. CENTRALIZED CAMPAIGN CONSTANTS & CONFIGURATION
// ==========================================================================
const campaignGoal = 1500.00;
const campaignRaised = 1466.58;
const campaignRemaining = Math.round((campaignGoal - campaignRaised) * 100) / 100; // 33.42
const campaignPercentage = (campaignRaised / campaignGoal) * 100; // 97.772%

const campaignConfig = {
  title: "Sementes do Amanhã — Juntos por um Novo Começo",
  goalMeta: campaignGoal,
  currentRaised: campaignRaised,
  remainingAmount: campaignRemaining,
  percentage: campaignPercentage,
  description: `ELAS NÃO ESCOLHERAM A FOME. MUITO MENOS A DOENÇA.

Enquanto tantas crianças brincam, comem e dormem tranquilas, outras enfrentam fome, abandono, falta de estrutura e doenças graves que nenhuma criança deveria conhecer.

São pequenos que deveriam estar pensando em brinquedos e sonhos, mas precisam enfrentar hospitais, tratamentos, medicamentos e dores que não deveriam fazer parte da infância.

Nossa ONG luta para oferecer comida, cuidados, tratamento e dignidade. Mas hoje, essas crianças precisam de você.

R$ 5, R$ 10 ou qualquer valor pode significar uma refeição, um medicamento, um tratamento ou simplesmente um pouco de esperança.

Se você pode ajudar, ajude. Não espere que outra pessoa faça por você.

E se não puder doar, compartilhe. Talvez um simples compartilhamento seu seja a ajuda que uma dessas crianças estava esperando.

Elas já enfrentam coisas demais. Não deixe que a falta de ajuda seja mais uma delas.

Doe por uma criança que só queria ter o direito de ser criança.`,
  videoOfferPrice: 8.99,
  donorCount: 51,
  heartCount: 68
};

// Expose globally for inspections/extensions
window.campaignGoal = campaignGoal;
window.campaignRaised = campaignRaised;
window.campaignRemaining = campaignRemaining;
window.campaignPercentage = campaignPercentage;
window.campaignConfig = campaignConfig;

// Centralized minimum goal completion threshold in integer cents (R$ 2,00)
const MIN_GOAL_COMPLETION_CENTS = 200;
window.MIN_GOAL_COMPLETION_CENTS = MIN_GOAL_COMPLETION_CENTS;

function getRemainingCents() {
  const goalCents = Math.round(campaignConfig.goalMeta * 100);
  const raisedCents = Math.round(campaignConfig.currentRaised * 100);
  return Math.max(0, goalCents - raisedCents);
}
window.getRemainingCents = getRemainingCents;

document.addEventListener('DOMContentLoaded', () => {
  // --- Toast Notification Helper ---
  const toast = document.getElementById('vk-toast');
  const toastMsg = document.getElementById('vk-toast-message');
  let toastTimeout = null;

  function showToast(message) {
    if (!toast) return;
    if (toastMsg) toastMsg.textContent = message;
    toast.classList.add('show');
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }
  window.showToast = showToast;

  // --- Copy to Clipboard for PIX and Links ---
  function copyTextToClipboard(text, successMsg) {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMsg || 'Copiado para a área de transferência!');
      }).catch(() => fallbackCopy(text, successMsg));
    } else {
      fallbackCopy(text, successMsg);
    }
  }

  function fallbackCopy(text, successMsg) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      showToast(successMsg || 'Copiado com sucesso!');
    } catch (err) {
      showToast('Erro ao copiar!');
    }
    document.body.removeChild(textArea);
  }

  // Attach to all elements with data-clipboard-text or copy classes
  document.querySelectorAll('[data-clipboard-text]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const text = el.getAttribute('data-clipboard-text');
      if (text) {
        copyTextToClipboard(text, 'Copiado com sucesso!');
      }
    });
  });

  // Attach to "Ver selos" link to activate selos tab
  const verSelosBtn = document.getElementById('ver-selos-btn') || document.querySelector('.sc-bf13f7ff-0 .kTFsLt');
  if (verSelosBtn) {
    verSelosBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const selosTabBtn = document.querySelector('.vk-tab-btn[data-tab="selos"]');
      if (selosTabBtn) {
        selosTabBtn.click();
        const tabsSection = document.querySelector('.sc-dhKdcB.iGWHkz');
        if (tabsSection) tabsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  // --- Tab Switching Logic ---
  const tabButtons = document.querySelectorAll('.vk-tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabButtons.forEach(b => {
        b.classList.remove('hpTUvZ');
        b.classList.add('fccSwh');
        const textDiv = b.querySelector('div');
        if (textDiv) {
          textDiv.classList.remove('bvrBZr');
          textDiv.classList.add('fGoREw');
        }
      });

      btn.classList.remove('fccSwh');
      btn.classList.add('hpTUvZ');
      const activeTextDiv = btn.querySelector('div');
      if (activeTextDiv) {
        activeTextDiv.classList.remove('fGoREw');
        activeTextDiv.classList.add('bvrBZr');
      }

      tabPanels.forEach(panel => {
        if (panel.id === `tab-${targetId}`) {
          panel.classList.add('active');
        } else {
          panel.classList.remove('active');
        }
      });
    });
  });

  // --- FAQ Accordion in "Perguntas e Respostas" Tab ---
  document.querySelectorAll('.vk-faq-question').forEach(q => {
    q.addEventListener('click', () => {
      const item = q.closest('.vk-faq-item');
      if (item) {
        item.classList.toggle('open');
      }
    });
  });

  // --- Heart Like Button Interaction ---
  const heartBtn = document.querySelector('[data-cy="give-sticker-button"]');
  const heartCountEl = document.getElementById('heart-count-value');
  let isLiked = false;
  let baseHearts = 9340;

  if (heartBtn) {
    heartBtn.addEventListener('click', () => {
      isLiked = !isLiked;
      heartBtn.classList.toggle('liked', isLiked);
      if (heartCountEl) {
        heartCountEl.textContent = isLiked ? (baseHearts + 1) : baseHearts;
      }
      showToast(isLiked ? 'Você enviou um coração para esta vaquinha!' : 'Coração removido');
    });
  }

  // --- "Ver tudo" / "Ver menos" Expander ---
  const shortDesc = document.getElementById('short-desc-text');
  let isExpanded = false;

  function setupVerTudo() {
    const verTudoBtn = document.getElementById('ver-tudo-btn');
    if (!verTudoBtn || !shortDesc) return;

    const heartCrackSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="#ef4444" stroke="#dc2626" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;display:inline-block;margin-right:4px"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="m12 13-1-1 2-2-3-3 2-2"/></svg>';
    const truncated = `${heartCrackSvg} ELAS NÃO ESCOLHERAM A FOME. MUITO MENOS A DOENÇA. Enquanto tantas crianças brincam, comem e dormem tranquilas, outras enfrentam fome, abandono, falta de estrutura e doenças graves que nenhuma criança deveria conhecer. `;
    const full = campaignConfig.description.replace(/\n\n/g, '<br><br>');

    verTudoBtn.onclick = (e) => {
      e.preventDefault();
      isExpanded = !isExpanded;
      if (isExpanded) {
        shortDesc.innerHTML = `${heartCrackSvg} ${full} <span class="sc-fqkvVR jKFlAz" id="ver-tudo-btn" style="cursor:pointer;font-weight:700">ver menos</span>`;
      } else {
        shortDesc.innerHTML = `${truncated}<span class="sc-fqkvVR jKFlAz" id="ver-tudo-btn" style="cursor:pointer;font-weight:700">ver tudo</span>`;
      }
      setupVerTudo();
    };
  }
  setupVerTudo();

  // --- Mobile Drawer Menu ---
  const burgerOpenBtn = document.getElementById('react-burger-menu-btn');
  const burgerCloseBtn = document.getElementById('react-burger-cross-btn');
  const menuWrap = document.querySelector('.bm-menu-wrap');
  const menuOverlay = document.querySelector('.bm-overlay');

  function openMobileMenu() {
    if (menuWrap) menuWrap.classList.add('open');
    if (menuOverlay) menuOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeMobileMenu() {
    if (menuWrap) menuWrap.classList.remove('open');
    if (menuOverlay) menuOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (burgerOpenBtn) burgerOpenBtn.addEventListener('click', openMobileMenu);
  if (burgerCloseBtn) burgerCloseBtn.addEventListener('click', closeMobileMenu);
  if (menuOverlay) menuOverlay.addEventListener('click', closeMobileMenu);

  // --- Floating Mini-Card Visibility Helpers ---
  function hideNormalMinicard() {
    const minicard = document.getElementById('vk-floating-minicard');
    if (minicard) {
      minicard.classList.remove('show');
      minicard.setAttribute('aria-hidden', 'true');
    }
  }
  window.hideNormalMinicard = hideNormalMinicard;

  function hideCheckoutRecoveryCard() {
    const recoveryCard = document.getElementById('vk-checkout-recovery-card');
    if (recoveryCard) {
      recoveryCard.classList.remove('show');
      recoveryCard.setAttribute('aria-hidden', 'true');
    }
  }
  window.hideCheckoutRecoveryCard = hideCheckoutRecoveryCard;

  // --- Modal Helpers ---
  function openModal(modalId) {
    hideNormalMinicard();
    hideCheckoutRecoveryCard();
    if (modalId === 'donate-modal' && typeof goToDonateStep === 'function') {
      goToDonateStep(1);
    }
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    }
    if (typeof updateMobileStickyState === 'function') updateMobileStickyState();
  }
  window.openModal = openModal;

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
      modal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
    if (typeof updateMobileStickyState === 'function') updateMobileStickyState();
  }
  window.closeModal = closeModal;

  // Close modals on close button or backdrop click
  document.querySelectorAll('.vk-modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.vk-modal-backdrop');
      if (modal) {
        if (modal.id === 'pix-checkout-modal' && typeof stopPixPolling === 'function') {
          stopPixPolling();
        }
        closeModal(modal.id);
        if (modal.id === 'pix-checkout-modal' && typeof handleCheckoutClosed === 'function') {
          handleCheckoutClosed();
        }
      }
    });
  });

  document.querySelectorAll('.vk-modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        if (backdrop.id === 'pix-checkout-modal' && typeof stopPixPolling === 'function') {
          stopPixPolling();
        }
        closeModal(backdrop.id);
        if (backdrop.id === 'pix-checkout-modal' && typeof handleCheckoutClosed === 'function') {
          handleCheckoutClosed();
        }
      }
    });
  });

  // --- Share Modal Trigger ---
  const shareButtons = document.querySelectorAll('[data-action="share"]');
  shareButtons.forEach(btn => {
    btn.addEventListener('click', () => openModal('share-modal'));
  });

  const copyShareLinkBtn = document.getElementById('copy-share-link-btn');
  const shareLinkInput = document.getElementById('share-link-input');
  if (copyShareLinkBtn && shareLinkInput) {
    copyShareLinkBtn.addEventListener('click', () => {
      copyTextToClipboard(shareLinkInput.value, 'Link da vaquinha copiado com sucesso!');
    });
  }

  // --- Deactivated / No-Action Handlers ---
  document.querySelectorAll('.vk-no-action').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });

  // --- Currency Formatter ---
  function formatBRL(value) {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }
  window.formatBRL = formatBRL;

  // --- Dynamic Goal & Campaign State Sync ---
  let hasAnimatedProgressBar = false;

  function updateGoalDisplay() {
    // Campaign sidebar elements
    const raisedEl = document.getElementById('raised-amount-val');
    const remainingEl = document.getElementById('goal-remaining-val');
    const remainingTextEl = document.getElementById('goal-remaining-text');
    const progressFill = document.getElementById('goal-progress-fill');
    const percentEl = document.getElementById('goal-progress-percent');
    const donorCountEl = document.getElementById('donor-count-val');

    // Calculate dynamic values strictly using integer cents
    const remainingCents = getRemainingCents();
    const remaining = remainingCents / 100;
    const current = Math.round(campaignConfig.currentRaised * 100) / 100;
    const meta = Math.round(campaignConfig.goalMeta * 100) / 100;
    campaignConfig.remainingAmount = remaining;

    const pct = Math.min(100, Math.round((current / meta) * 100));

    if (raisedEl) raisedEl.textContent = formatBRL(current);
    if (percentEl) percentEl.textContent = `${pct}%`;

    const targetWidth = `${(current / meta) * 100}%`;
    if (progressFill) {
      if (!hasAnimatedProgressBar) {
        const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (prefersReducedMotion) {
          progressFill.style.transition = 'none';
          progressFill.style.width = targetWidth;
          hasAnimatedProgressBar = true;
        } else {
          progressFill.style.width = '0%';
          progressFill.style.transition = 'width 0.9s cubic-bezier(0.16, 1, 0.3, 1)';
          setTimeout(() => {
            progressFill.style.width = targetWidth;
            hasAnimatedProgressBar = true;
          }, 150);
        }
      } else {
        progressFill.style.width = targetWidth;
      }
    }

    if (remaining <= 0 && remainingTextEl) {
      remainingTextEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#f59e0b" stroke="#d97706" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px;display:inline-block;margin-right:4px"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg> <strong>Meta alcançada!</strong> Obrigado a todos os apoiadores!`;
    } else if (remainingTextEl) {
      if (pct >= 90) {
        remainingTextEl.innerHTML = `Faltam só <strong class="vk-urgency-val" id="goal-remaining-val">${formatBRL(remaining)}</strong> para a meta`;
      } else {
        remainingTextEl.innerHTML = `Faltam <strong class="vk-urgency-val" id="goal-remaining-val">${formatBRL(remaining)}</strong> para a meta`;
      }
    } else if (remainingEl) {
      remainingEl.textContent = formatBRL(remaining);
    }

    // Synchronize CRO Elements
    const minicardRemaining = document.getElementById('minicard-remaining-val');
    const exitIntentRemaining = document.getElementById('exit-intent-remaining-val');
    const mobileStickyRemaining = document.getElementById('mobile-sticky-remaining-val');
    if (minicardRemaining) minicardRemaining.textContent = formatBRL(remaining);
    if (exitIntentRemaining) exitIntentRemaining.textContent = formatBRL(remaining);
    if (mobileStickyRemaining) mobileStickyRemaining.textContent = formatBRL(remaining);

    if (donorCountEl) donorCountEl.textContent = campaignConfig.donorCount.toLocaleString('pt-BR');
    const heartCountEl = document.getElementById('heart-count-value');
    if (heartCountEl) heartCountEl.textContent = (campaignConfig.heartCount || 68).toLocaleString('pt-BR');
    const quemAjudouCountEl = document.getElementById('quem-ajudou-count-header');
    if (quemAjudouCountEl) quemAjudouCountEl.textContent = `${campaignConfig.donorCount} pessoas já apoiaram esta vaquinha`;

    // Synchronize Post-Donation Modal Elements
    const postRemainingDisplay = document.getElementById('post-remaining-display');
    const postMetricRaised = document.getElementById('post-metric-raised');
    const postMetricGoal = document.getElementById('post-metric-goal');
    const postMetricRemaining = document.getElementById('post-metric-remaining');
    const postProgressFill = document.getElementById('post-modal-progress-fill');
    const postBtnComplete = document.getElementById('post-btn-complete');
    const postVideoPriceDisplay = document.getElementById('post-video-price-display');
    const postBtnBuyVideo = document.getElementById('post-btn-buy-video');

    if (postRemainingDisplay) postRemainingDisplay.textContent = formatBRL(remaining);
    if (postMetricRaised) postMetricRaised.textContent = formatBRL(current);
    if (postMetricGoal) postMetricGoal.textContent = formatBRL(meta);
    if (postMetricRemaining) postMetricRemaining.textContent = formatBRL(remaining);
    if (postProgressFill) postProgressFill.style.width = `${(current / meta) * 100}%`;
    if (postBtnComplete) postBtnComplete.textContent = `Completar com ${formatBRL(remaining)}`;
    if (postVideoPriceDisplay) postVideoPriceDisplay.textContent = formatBRL(campaignConfig.videoOfferPrice);
    if (postBtnBuyVideo) postBtnBuyVideo.textContent = `Quero receber meu vídeo por ${formatBRL(campaignConfig.videoOfferPrice)}`;
  }
  window.updateGoalDisplay = updateGoalDisplay;

  // Initial goal render
  updateGoalDisplay();

  // ==========================================================================
  // 2. POST-DONATION MULTI-STEP FLOW CONTROLLER
  // ==========================================================================
  function openPostDonationFlow(step = 'payment-approved') {
    closeModal('donate-modal');
    sessionStorage.setItem('vk_donation_completed', '1');
    const minicard = document.getElementById('vk-floating-minicard');
    if (minicard) {
      minicard.classList.remove('show');
      minicard.setAttribute('aria-hidden', 'true');
    }

    // Minimum goal completion threshold rule:
    // If remaining < MIN_GOAL_COMPLETION_CENTS (or <= 0), NEVER show the completion screen,
    // go DIRECTLY to video-offer!
    const remainingCents = getRemainingCents();
    if ((step === 'payment-approved' || step === 'approved') && remainingCents < MIN_GOAL_COMPLETION_CENTS) {
      step = 'video-offer';
    }

    // Deactivate all steps
    document.querySelectorAll('.vk-post-step').forEach(s => s.classList.remove('active'));

    if (step === 'payment-approved' || step === 'approved') {
      const s = document.getElementById('post-step-approved');
      if (s) s.classList.add('active');
    } else if (step === 'video-offer' || step === 'video') {
      const s = document.getElementById('post-step-video');
      if (s) s.classList.add('active');
    } else if (step === 'finished' || step === 'success') {
      const s = document.getElementById('post-step-finished');
      if (s) s.classList.add('active');
    }

    openModal('post-donation-modal');
  }
  window.openPostDonationFlow = openPostDonationFlow;

  // --- Primary Donation Modal ("Quero Ajudar" & "Doar") ---
  const donateButtons = document.querySelectorAll('[data-action="donate"]');
  donateButtons.forEach(btn => {
    btn.addEventListener('click', () => openModal('donate-modal'));
  });

  const amountOptions = document.querySelectorAll('.vk-amount-option');
  const customAmountInput = document.getElementById('custom-donation-input');

  amountOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      amountOptions.forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      const val = opt.getAttribute('data-val');
      const numVal = parseFloat(val);
      if (customAmountInput) {
        if (!isNaN(numVal)) {
          customAmountInput.value = numVal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        } else {
          customAmountInput.value = `R$ ${val}`;
        }
      }
    });
  });

  if (customAmountInput) {
    customAmountInput.addEventListener('input', () => {
      let rawVal = customAmountInput.value.replace(/[^\d,.-]/g, '');
      if (rawVal.includes(',')) {
        rawVal = rawVal.replace(/\./g, '').replace(',', '.');
      }
      const numVal = parseFloat(rawVal);
      amountOptions.forEach(o => {
        const optVal = parseFloat(o.getAttribute('data-val'));
        if (!isNaN(optVal) && !isNaN(numVal) && Math.abs(optVal - numVal) < 0.01) {
          o.classList.add('selected');
        } else {
          o.classList.remove('selected');
        }
      });
    });
  }

  // =========================================================================
  // 2-STEP DONATION MODAL CONTROLLER
  // ==========================================================================
  const donateStep1 = document.getElementById('donate-step-1');
  const donateStep2 = document.getElementById('donate-step-2');
  const donateStep1NextBtn = document.getElementById('donate-step1-next-btn');
  const donateStep2BackBtn = document.getElementById('donate-step2-back-btn');
  const donateStep2EditBtn = document.getElementById('donate-step2-edit-amount-btn');
  const donateStepBadge = document.getElementById('donate-step-badge');
  const dotStep1 = document.getElementById('dot-step-1');
  const lineStep12 = document.getElementById('line-step-1-2');
  const dotStep2 = document.getElementById('dot-step-2');
  const donateStep2AmountDisplay = document.getElementById('donate-step2-amount-display');

  function getSelectedDonationAmount() {
    let amount = 33.42;
    if (customAmountInput) {
      let clean = customAmountInput.value.replace(/[^\d,.-]/g, '');
      if (clean.includes(',')) {
        clean = clean.replace(/\./g, '').replace(',', '.');
      }
      const parsed = parseFloat(clean);
      if (!isNaN(parsed) && parsed > 0) {
        amount = Math.min(parsed, 1000.0);
      }
    }
    return amount;
  }
  window.getSelectedDonationAmount = getSelectedDonationAmount;

  function goToDonateStep(stepNum) {
    const modalBody = document.querySelector('.vk-donate-modal-body') || document.querySelector('.vk-modal-body');
    if (stepNum === 1) {
      if (donateStep1) donateStep1.style.display = 'block';
      if (donateStep2) donateStep2.style.display = 'none';
      if (donateStep2BackBtn) donateStep2BackBtn.style.display = 'none';
      if (donateStepBadge) donateStepBadge.textContent = 'Etapa 1 de 2';
      if (dotStep1) dotStep1.classList.add('active');
      if (lineStep12) lineStep12.classList.remove('active');
      if (dotStep2) dotStep2.classList.remove('active');
      if (modalBody) modalBody.scrollTop = 0;
    } else if (stepNum === 2) {
      const amt = getSelectedDonationAmount();
      if (donateStep2AmountDisplay) {
        donateStep2AmountDisplay.textContent = formatBRL(amt);
      }
      if (donateStep1) donateStep1.style.display = 'none';
      if (donateStep2) donateStep2.style.display = 'block';
      if (donateStep2BackBtn) donateStep2BackBtn.style.display = 'inline-flex';
      if (donateStepBadge) donateStepBadge.textContent = 'Etapa 2 de 2';
      if (dotStep1) dotStep1.classList.add('active');
      if (lineStep12) lineStep12.classList.add('active');
      if (dotStep2) dotStep2.classList.add('active');
      if (modalBody) modalBody.scrollTop = 0;
      // Proactively clear previous validation error if any
      const err = document.getElementById('donor-form-error');
      if (err) { err.style.display = 'none'; err.textContent = ''; }
      setTimeout(() => {
        const nameInput = document.getElementById('donor-name');
        if (nameInput && !nameInput.value) {
          nameInput.focus();
        }
      }, 120);
    }
  }
  window.goToDonateStep = goToDonateStep;

  if (donateStep1NextBtn) {
    donateStep1NextBtn.addEventListener('click', (e) => {
      e.preventDefault();
      goToDonateStep(2);
    });
  }

  if (donateStep2BackBtn) {
    donateStep2BackBtn.addEventListener('click', (e) => {
      e.preventDefault();
      goToDonateStep(1);
    });
  }

  if (donateStep2EditBtn) {
    donateStep2EditBtn.addEventListener('click', (e) => {
      e.preventDefault();
      goToDonateStep(1);
    });
  }

  // Modern Anonymous Contribution Checkbox / Switch
  const anonCard = document.getElementById('anonymous-toggle-card');
  let isAnonymousChecked = false;
  try {
    isAnonymousChecked = localStorage.getItem('vk_is_anonymous') === '1';
  } catch (_) {}

  function updateAnonUI(checked) {
    if (!anonCard) return;
    isAnonymousChecked = checked;
    anonCard.setAttribute('aria-checked', checked ? 'true' : 'false');
    const badge = anonCard.querySelector('.vk-anon-badge');
    if (checked) {
      anonCard.classList.add('checked');
      if (badge) badge.style.display = 'inline-flex';
    } else {
      anonCard.classList.remove('checked');
      if (badge) badge.style.display = 'none';
    }
    try {
      localStorage.setItem('vk_is_anonymous', checked ? '1' : '0');
    } catch (_) {}
  }

  if (anonCard) {
    updateAnonUI(isAnonymousChecked);
    anonCard.addEventListener('click', () => {
      updateAnonUI(!isAnonymousChecked);
    });
    anonCard.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        updateAnonUI(!isAnonymousChecked);
      }
    });
  }

    // =========================================================================
  // BLACKCAT PIX PAYMENT CONTROLLER
  // ==========================================================================
  let activePollingTimer = null;
  let currentActivePaymentId = null;
  let currentActivePaymentAmount = 25;
  let currentActivePaymentType = 'donation';
  let currentActivePaymentOnSuccess = null;

  // Donor form elements (Required by Blackcat / BACEN for Pix creation)
  const donorNameInput = document.getElementById('donor-name');
  const donorCpfInput = document.getElementById('donor-cpf');
  const donorPhoneInput = document.getElementById('donor-phone');
  const donorEmailInput = document.getElementById('donor-email');
  const donorErrorEl = document.getElementById('donor-form-error');

  // Masks for Brazilian document & phone
  function maskCPF(value) {
    return value
      .replace(/\D/g, '')
      .slice(0, 11)
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  }

  function maskPhone(value) {
    const digits = value.replace(/\D/g, '').slice(0, 11);
    if (digits.length <= 10) {
      return digits
        .replace(/(\d{2})(\d)/, '($1) $2')
        .replace(/(\d{4})(\d)/, '$1-$2');
    }
    return digits
      .replace(/(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{5})(\d{4})$/, '$1-$2');
  }

  function isValidCPF(cpf) {
    const clean = cpf.replace(/\D/g, '');
    if (clean.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(clean)) return false;
    let sum = 0;
    for (let i = 0; i < 9; i++) sum += parseInt(clean.charAt(i), 10) * (10 - i);
    let rev = 11 - (sum % 11);
    if (rev === 10 || rev === 11) rev = 0;
    if (rev !== parseInt(clean.charAt(9), 10)) return false;
    sum = 0;
    for (let i = 0; i < 10; i++) sum += parseInt(clean.charAt(i), 10) * (11 - i);
    rev = 11 - (sum % 11);
    if (rev === 10 || rev === 11) rev = 0;
    return rev === parseInt(clean.charAt(10), 10);
  }

  function getUtmParams() {
    const params = new URLSearchParams(window.location.search);
    const utms = {};
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(k => {
      const v = params.get(k);
      if (v) utms[k] = v;
    });
    return utms;
  }

  // Pre-fill and save to localStorage
  try {
    if (donorNameInput && !donorNameInput.value) donorNameInput.value = localStorage.getItem('vk_donor_name') || '';
    if (donorCpfInput && !donorCpfInput.value) donorCpfInput.value = localStorage.getItem('vk_donor_cpf') || '';
    if (donorPhoneInput && !donorPhoneInput.value) donorPhoneInput.value = localStorage.getItem('vk_donor_phone') || '';
    if (donorEmailInput && !donorEmailInput.value) donorEmailInput.value = localStorage.getItem('vk_donor_email') || '';
  } catch (e) {}

  if (donorCpfInput) {
    donorCpfInput.addEventListener('input', (e) => {
      e.target.value = maskCPF(e.target.value);
      try { localStorage.setItem('vk_donor_cpf', e.target.value); } catch (_) {}
      if (donorErrorEl) donorErrorEl.style.display = 'none';
    });
  }
  if (donorPhoneInput) {
    donorPhoneInput.addEventListener('input', (e) => {
      e.target.value = maskPhone(e.target.value);
      try { localStorage.setItem('vk_donor_phone', e.target.value); } catch (_) {}
      if (donorErrorEl) donorErrorEl.style.display = 'none';
    });
  }
  if (donorNameInput) {
    donorNameInput.addEventListener('input', (e) => {
      try { localStorage.setItem('vk_donor_name', e.target.value); } catch (_) {}
      if (donorErrorEl) donorErrorEl.style.display = 'none';
    });
  }
  if (donorEmailInput) {
    donorEmailInput.addEventListener('input', (e) => {
      try { localStorage.setItem('vk_donor_email', e.target.value); } catch (_) {}
      if (donorErrorEl) donorErrorEl.style.display = 'none';
    });
  }

  function getDonorInfo(validate = true) {
    const name = (donorNameInput?.value || localStorage.getItem('vk_donor_name') || '').trim();
    const cpf = (donorCpfInput?.value || localStorage.getItem('vk_donor_cpf') || '').trim();
    const phone = (donorPhoneInput?.value || localStorage.getItem('vk_donor_phone') || '').trim();
    const email = (donorEmailInput?.value || localStorage.getItem('vk_donor_email') || '').trim();

    if (donorErrorEl) {
      donorErrorEl.style.display = 'none';
      donorErrorEl.textContent = '';
    }

    if (validate) {
      if (!name || name.length < 3) {
        if (donorErrorEl) {
          donorErrorEl.textContent = 'Por favor, informe seu nome completo.';
          donorErrorEl.style.display = 'block';
        }
        donorNameInput?.focus();
        return null;
      }
      const cleanCpf = cpf.replace(/\D/g, '');
      if (cleanCpf.length !== 11 || !isValidCPF(cleanCpf)) {
        if (donorErrorEl) {
          donorErrorEl.textContent = 'Por favor, informe um CPF válido para identificação do Pix.';
          donorErrorEl.style.display = 'block';
        }
        donorCpfInput?.focus();
        return null;
      }
      const cleanPhone = phone.replace(/\D/g, '');
      if (cleanPhone.length < 10) {
        if (donorErrorEl) {
          donorErrorEl.textContent = 'Por favor, informe seu telefone com DDD.';
          donorErrorEl.style.display = 'block';
        }
        donorPhoneInput?.focus();
        return null;
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        if (donorErrorEl) {
          donorErrorEl.textContent = 'Por favor, informe um e-mail válido para receber o comprovante.';
          donorErrorEl.style.display = 'block';
        }
        donorEmailInput?.focus();
        return null;
      }
    }

    return {
      name: name || 'Apoiador Solidário',
      document: cpf.replace(/\D/g, '') || '11144477735',
      phone: phone.replace(/\D/g, '') || '11998765432',
      email: email || 'doador@ajude-vakinha.com'
    };
  }

  function stopPixPolling() {
    if (activePollingTimer) {
      clearInterval(activePollingTimer);
      activePollingTimer = null;
    }
  }
  window.stopPixPolling = stopPixPolling;

  function startPixPolling(paymentId, type, amount, onSuccess) {
    stopPixPolling();
    const pid = paymentId || currentActivePaymentId;
    if (!pid) return;

    const cb = onSuccess || currentActivePaymentOnSuccess;
    activePollingTimer = setInterval(() => {
      fetch(`/api/payments/${pid}/status`)
        .then(res => res.json())
        .then(statusData => {
          if (statusData.status === 'paid') {
            stopPixPolling();
            sessionStorage.setItem('vk_donation_completed', '1');
            sessionStorage.removeItem('vk_checkout_abandoned');
            hideNormalMinicard();
            hideCheckoutRecoveryCard();

            const statusText = document.getElementById('pix-checkout-status-text');
            if (statusText) statusText.textContent = 'Pagamento aprovado!';
            showToast('Pagamento confirmado com sucesso via Pix!');

            setTimeout(() => {
              closeModal('pix-checkout-modal');
              if (typeof cb === 'function') {
                cb(statusData);
              }
            }, 600);
          }
        })
        .catch(err => {
          console.error('Erro na consulta de status do Pix:', err);
        });
    }, 3000);
  }
  window.startPixPolling = startPixPolling;

  function startPixPayment(type, amount, extraMeta = {}, onPaidSuccess) {
    stopPixPolling();
    currentActivePaymentId = null;
    currentActivePaymentAmount = amount;
    currentActivePaymentType = type;
    currentActivePaymentOnSuccess = onPaidSuccess;

    // Reset PIX modal state
    const pixAmountEl = document.getElementById('pix-checkout-amount');
    const qrImg = document.getElementById('pix-qr-image');
    const qrSkeleton = document.getElementById('pix-qr-loading');
    const copyInput = document.getElementById('pix-copy-paste-input');
    const statusText = document.getElementById('pix-checkout-status-text');
    const copyBtn = document.getElementById('pix-copy-btn');

    if (pixAmountEl) pixAmountEl.textContent = formatBRL(amount);
    if (qrImg) {
      qrImg.src = '';
      qrImg.style.display = 'none';
    }
    if (qrSkeleton) {
      qrSkeleton.innerHTML = `
        <div class="vk-pix-spinner"></div>
        <span>Gerando cobrança Pix oficial...</span>
      `;
      qrSkeleton.classList.remove('hidden');
      qrSkeleton.style.display = 'flex';
    }
    if (copyInput) copyInput.value = '';
    if (statusText) statusText.textContent = 'Aguardando pagamento...';
    if (copyBtn) {
      copyBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copiar</span>
      `;
    }

    openModal('pix-checkout-modal');

    // Retrieve donor info from extraMeta or localStorage/form
    const donor = {
      name: extraMeta.name || localStorage.getItem('vk_donor_name') || 'Apoiador Solidário',
      document: (extraMeta.document || localStorage.getItem('vk_donor_cpf') || '11144477735').replace(/\D/g, ''),
      phone: (extraMeta.phone || localStorage.getItem('vk_donor_phone') || '11998765432').replace(/\D/g, ''),
      email: extraMeta.email || localStorage.getItem('vk_donor_email') || 'doador@ajude-vakinha.com'
    };

    // Call backend endpoint to generate PIX via Blackcat
    const payload = {
      type: type,
      amount: amount,
      customer: {
        name: donor.name,
        cpf: donor.document,
        phone: donor.phone,
        email: donor.email
      },
      payer_name: donor.name,
      payer_document: donor.document,
      payer_phone: donor.phone,
      payer_email: donor.email,
      utms: getUtmParams()
    };

    fetch('/api/payments/pix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(async res => {
      const data = await res.json();
      if (!res.ok || (!data.success && !data.id && !data.transactionId)) {
        throw new Error(data.message || data.error || 'Não foi possível gerar o Pix agora. Tente novamente em alguns instantes.');
      }
      return data;
    })
    .then(data => {
      const paymentObj = data.payment || data;
      currentActivePaymentId = paymentObj.transactionId || paymentObj.id || data.transactionId || data.id;

      // Update QR Code
      let qrSource = paymentObj.qrCodeBase64 || paymentObj.qrImageUrl || paymentObj.qr_code_image_url || paymentObj.qrBase64 || paymentObj.qr_code_base64 || data.qrCodeBase64;
      const copyPasteCode = paymentObj.copyPaste || paymentObj.pixCopyPaste || paymentObj.qr_code_text || data.copyPaste || '';

      // Fallback: If no direct image URL was provided, generate standard QR image from real PIX EMV code
      if (!qrSource && copyPasteCode) {
        qrSource = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(copyPasteCode)}`;
      }

      if (qrImg && qrSource) {
        if (qrSource.startsWith('data:') || qrSource.startsWith('http://') || qrSource.startsWith('https://')) {
          qrImg.src = qrSource;
        } else {
          qrImg.src = `data:image/png;base64,${qrSource}`;
        }
        qrImg.style.display = 'block';
      }
      if (qrSkeleton) {
        qrSkeleton.classList.add('hidden');
        qrSkeleton.style.display = 'none';
      }

      // Update Copia e Cola
      if (copyInput) {
        copyInput.value = copyPasteCode;
      }

      // Setup Copy Button
      if (copyBtn) {
        copyBtn.onclick = () => {
          if (copyInput && copyInput.value) {
            copyTextToClipboard(copyInput.value, 'Código Pix copiado com sucesso!');
            copyBtn.innerHTML = `
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 6L9 17l-5-5"></path>
              </svg>
              <span>Copiado!</span>
            `;
            setTimeout(() => {
              copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span>Copiar</span>
              `;
            }, 2500);
          }
        };
      }

      // Start Polling every 3 seconds
      startPixPolling(currentActivePaymentId, type, amount, onPaidSuccess);
    })
    .catch(err => {
      console.error('Erro ao gerar cobrança Pix:', err);
      const userMsg = err.message || 'Não foi possível gerar o Pix agora. Tente novamente em alguns instantes.';
      showToast(userMsg);
      if (qrSkeleton) {
        qrSkeleton.innerHTML = `
          <div style="text-align:center;padding:12px 14px;color:#dc2626;display:flex;flex-direction:column;align-items:center;gap:8px;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span style="font-size:12px;font-weight:600;line-height:1.4">${userMsg}</span>
            <button type="button" id="pix-retry-btn" style="background:#009d4e;color:#fff;border:none;border-radius:20px;padding:6px 16px;font-family:'Montserrat',sans-serif;font-size:11.5px;font-weight:700;cursor:pointer;margin-top:2px;">Tentar novamente</button>
          </div>
        `;
        const retryBtn = document.getElementById('pix-retry-btn');
        if (retryBtn) {
          retryBtn.onclick = () => {
            qrSkeleton.innerHTML = `
              <div class="vk-pix-spinner"></div>
              <span>Gerando cobrança Pix...</span>
            `;
            startPixPayment(type, amount, extraMeta, onPaidSuccess);
          };
        }
      }
    });
  }
  window.startPixPayment = startPixPayment;

  // Setup Close Pix Modal
  const pixCheckoutCloseBtn = document.getElementById('pix-checkout-close');
  if (pixCheckoutCloseBtn) {
    pixCheckoutCloseBtn.addEventListener('click', () => {
      stopPixPolling();
      closeModal('pix-checkout-modal');
      if (typeof handleCheckoutClosed === 'function') {
        handleCheckoutClosed();
      }
    });
  }

  // --- Confirm First Donation with PIX -> Advances to Post-Donation Flow ---
  const confirmDonateBtn = document.getElementById('confirm-donate-btn');
  if (confirmDonateBtn) {
    confirmDonateBtn.addEventListener('click', () => {
      if (confirmDonateBtn.disabled) return;

      const donorInfo = getDonorInfo(true);
      if (!donorInfo) return; // Validation failed, error is displayed on donor form

      confirmDonateBtn.disabled = true;
      const originalText = confirmDonateBtn.textContent;
      confirmDonateBtn.textContent = 'Gerando Pix...';

      const amount = getSelectedDonationAmount();

      closeModal('donate-modal');
      goToDonateStep(1); // Reset for next time
      confirmDonateBtn.disabled = false;
      confirmDonateBtn.textContent = originalText;

      startPixPayment('donation', amount, donorInfo, (paidData) => {
        const donationCents = Math.round(amount * 100);
        const currentRaisedCents = Math.round(campaignConfig.currentRaised * 100) + donationCents;
        campaignConfig.currentRaised = currentRaisedCents / 100;
        campaignConfig.donorCount += 1;
        updateGoalDisplay();

        const remainingCents = getRemainingCents();
        if (remainingCents >= MIN_GOAL_COMPLETION_CENTS) {
          openPostDonationFlow('payment-approved');
        } else {
          openPostDonationFlow('video-offer');
        }
      });
    });
  }

    // ==========================================================================
  // 3. STEP 1 ACTIONS (PAGAMENTO APROVADO)
  // ==========================================================================

  // Action: "Completar com R$ XX,XX"
  const postBtnComplete = document.getElementById('post-btn-complete');
  if (postBtnComplete) {
    postBtnComplete.addEventListener('click', () => {
      if (postBtnComplete.disabled) return;
      const remainingCents = getRemainingCents();
      if (remainingCents < MIN_GOAL_COMPLETION_CENTS) {
        openPostDonationFlow('video-offer');
        return;
      }
      const remaining = remainingCents / 100;

      postBtnComplete.disabled = true;
      const origText = postBtnComplete.textContent;
      postBtnComplete.textContent = 'Gerando PIX...';

      closeModal('post-donation-modal');
      postBtnComplete.disabled = false;
      postBtnComplete.textContent = origText;

      const dInfo = (typeof getDonorInfo === 'function' ? getDonorInfo(false) : null) || {};
      startPixPayment('goal_completion', remaining, dInfo, (paidData) => {
        const goalCents = Math.round(campaignConfig.goalMeta * 100);
        const completionCents = Math.round(remaining * 100);
        const newRaisedCents = Math.min(goalCents, Math.round(campaignConfig.currentRaised * 100) + completionCents);
        campaignConfig.currentRaised = newRaisedCents / 100;
        updateGoalDisplay();
        openPostDonationFlow('video-offer');
      });
    });
  }

  // Action: "Agora não" -> Advances to Screen 2 (Video Offer)
  const postBtnNotNow = document.getElementById('post-btn-not-now');
  if (postBtnNotNow) {
    postBtnNotNow.addEventListener('click', () => {
      // Do NOT close! Open Screen 2
      openPostDonationFlow('video-offer');
    });
  }

  // ==========================================================================
  // 4. STEP 2 ACTIONS (VÍDEO DE AGRADECIMENTO)
  // ==========================================================================

  // Non-functional Play Button on Video Player Mockup
  const videoPlayBtn = document.getElementById('vk-video-play-button');
  if (videoPlayBtn) {
    videoPlayBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      showToast('Prévia do vídeo ilustrativa.');
    });
  }

  // Action: "Quero receber meu vídeo por R$ 8,99"
  const postBtnBuyVideo = document.getElementById('post-btn-buy-video');
  if (postBtnBuyVideo) {
    postBtnBuyVideo.addEventListener('click', () => {
      if (postBtnBuyVideo.disabled) return;
      const videoPrice = campaignConfig.videoOfferPrice; // 8.99

      postBtnBuyVideo.disabled = true;
      const origText = postBtnBuyVideo.textContent;
      postBtnBuyVideo.textContent = 'Gerando PIX...';

      closeModal('post-donation-modal');
      postBtnBuyVideo.disabled = false;
      postBtnBuyVideo.textContent = origText;

      const dInfo = (typeof getDonorInfo === 'function' ? getDonorInfo(false) : null) || {};
      startPixPayment('thank_you_video', videoPrice, dInfo, (paidData) => {
        openPostDonationFlow('finished');
      });
    });
  }

  // Action: "Continuar sem o vídeo" -> Closes flow & returns to campaign
  const postBtnSkipVideo = document.getElementById('post-btn-skip-video');
  if (postBtnSkipVideo) {
    postBtnSkipVideo.addEventListener('click', (e) => {
      e.preventDefault();
      closeModal('post-donation-modal');
      showToast('Obrigado por apoiar a campanha Sementes do Amanhã!');
    });
  }

  // ==========================================================================
  // 5. STEP 3 ACTIONS (FINAL / CONCLUIR)
  // ==========================================================================
  const postBtnFinish = document.getElementById('post-btn-finish');
  if (postBtnFinish) {
    postBtnFinish.addEventListener('click', () => {
      closeModal('post-donation-modal');
      showToast('Obrigado por fazer a diferença na vida das crianças!');
    });
  }

  const postModalCloseBtn = document.getElementById('post-modal-close-btn');
  if (postModalCloseBtn) {
    postModalCloseBtn.addEventListener('click', () => {
      closeModal('post-donation-modal');
    });
  }

  // ==========================================================================
  // 6. CRO: FLOATING MINI-CARDS & POP-UP PRIORITY CONTROLLER
  // ==========================================================================
  function isCheckoutActive() {
    const checkoutModal = document.getElementById('pix-checkout-modal');
    return !!(checkoutModal && checkoutModal.classList.contains('active'));
  }
  window.isCheckoutActive = isCheckoutActive;

  function isPostPaymentActive() {
    const postModal = document.getElementById('post-donation-modal');
    return !!(postModal && postModal.classList.contains('active')) || sessionStorage.getItem('vk_donation_completed') === '1';
  }
  window.isPostPaymentActive = isPostPaymentActive;

  function isExitIntentActive() {
    const exitModal = document.getElementById('vk-exit-intent-modal');
    return !!(exitModal && exitModal.classList.contains('active'));
  }
  window.isExitIntentActive = isExitIntentActive;

  function isCheckoutAbandoned() {
    return sessionStorage.getItem('vk_checkout_abandoned') === '1';
  }
  window.isCheckoutAbandoned = isCheckoutAbandoned;

  function showCheckoutRecoveryCard() {
    // Priority 1: checkout or post-payment active -> no mini-card
    if (isCheckoutActive() || isPostPaymentActive()) return;
    if (sessionStorage.getItem('vk_donation_completed') === '1') return;
    if (sessionStorage.getItem('vk_recovery_dismissed') === '1') return;
    if (isExitIntentActive()) return;

    // Priority 2: checkout abandonment has priority over normal minicard
    hideNormalMinicard();

    const recoveryCard = document.getElementById('vk-checkout-recovery-card');
    if (recoveryCard) {
      const recAmtEl = document.getElementById('recovery-amount-val');
      if (recAmtEl && currentActivePaymentAmount) {
        recAmtEl.textContent = formatBRL(currentActivePaymentAmount);
      }
      recoveryCard.classList.add('show');
      recoveryCard.setAttribute('aria-hidden', 'false');
    }
  }
  window.showCheckoutRecoveryCard = showCheckoutRecoveryCard;

  function handleCheckoutClosed() {
    if (sessionStorage.getItem('vk_donation_completed') !== '1') {
      sessionStorage.setItem('vk_checkout_abandoned', '1');
      closeModal('pix-checkout-modal');
      showCheckoutRecoveryCard();
    }
  }
  window.handleCheckoutClosed = handleCheckoutClosed;

  function tryShowNormalMinicard() {
    // Disable floating minicards on mobile (mobile uses bottom sticky bar exclusively)
    if (window.innerWidth <= 768) return;

    // Priority 1: checkout / post-payment active -> no mini-card
    if (isCheckoutActive() || isPostPaymentActive()) return;
    if (sessionStorage.getItem('vk_donation_completed') === '1') return;

    // Priority 2: checkout abandonment has priority over normal minicard
    if (isCheckoutAbandoned() && sessionStorage.getItem('vk_recovery_dismissed') !== '1') {
      showCheckoutRecoveryCard();
      return;
    }

    // Priority 3: exit intent has priority over normal minicard
    if (isExitIntentActive()) return;

    // Any modal active?
    if (document.querySelector('.vk-modal-backdrop.active')) return;

    // Dismissed in current session?
    if (sessionStorage.getItem('vk_minicard_dismissed') === '1') return;

    // Priority 4: Normal navigation -> show normal lateral mini-card
    const floatingMinicard = document.getElementById('vk-floating-minicard');
    if (floatingMinicard) {
      floatingMinicard.classList.add('show');
      floatingMinicard.setAttribute('aria-hidden', 'false');
    }
  }
  window.tryShowNormalMinicard = tryShowNormalMinicard;

  // Schedule normal minicard after 5 seconds (between 4 and 6 seconds)
  setTimeout(() => {
    tryShowNormalMinicard();
  }, 5000);

  // Normal minicard listeners
  const floatingMinicard = document.getElementById('vk-floating-minicard');
  const minicardCloseBtn = document.getElementById('vk-minicard-close-btn');

  if (minicardCloseBtn) {
    minicardCloseBtn.addEventListener('click', () => {
      hideNormalMinicard();
      sessionStorage.setItem('vk_minicard_dismissed', '1');
    });
  }

  const minicardDonateBtn = document.querySelector('#vk-floating-minicard [data-action="donate"]');
  if (minicardDonateBtn) {
    minicardDonateBtn.addEventListener('click', () => {
      hideNormalMinicard();
      sessionStorage.setItem('vk_minicard_dismissed', '1');
      openModal('donate-modal');
    });
  }

  // Recovery card listeners
  const recoveryCloseBtn = document.getElementById('vk-recovery-close-btn');
  if (recoveryCloseBtn) {
    recoveryCloseBtn.addEventListener('click', () => {
      hideCheckoutRecoveryCard();
      sessionStorage.setItem('vk_recovery_dismissed', '1');
    });
  }

  const recoveryResumeBtn = document.getElementById('vk-recovery-resume-btn');
  if (recoveryResumeBtn) {
    recoveryResumeBtn.addEventListener('click', () => {
      hideCheckoutRecoveryCard();
      openModal('pix-checkout-modal');
      if (currentActivePaymentId && !activePollingTimer) {
        startPixPolling(currentActivePaymentId, currentActivePaymentType, currentActivePaymentAmount, currentActivePaymentOnSuccess);
      }
    });
  }

  // ==========================================================================
  // 7. CRO: DESKTOP EXIT-INTENT TRIGGER (MOUSELEAVE TOP <= 15PX)
  // ==========================================================================
  const exitIntentModal = document.getElementById('vk-exit-intent-modal');
  const exitIntentDonateBtn = document.getElementById('exit-intent-donate-btn');
  const exitIntentDismissBtn = document.getElementById('exit-intent-dismiss-btn');

  if (exitIntentModal) {
    function handleExitIntent(e) {
      if (window.innerWidth >= 992 && e.clientY <= 15) {
        const isShown = sessionStorage.getItem('vk_exit_intent_shown') === '1';
        const hasDonated = sessionStorage.getItem('vk_donation_completed') === '1';
        const hasActiveModal = document.querySelector('.vk-modal-backdrop.active');

        if (!isShown && !hasDonated && !hasActiveModal) {
          sessionStorage.setItem('vk_exit_intent_shown', '1');
          document.removeEventListener('mouseleave', handleExitIntent);
          // Priority 3: Exit-intent has priority over lateral mini-cards
          hideNormalMinicard();
          hideCheckoutRecoveryCard();
          exitIntentModal.classList.add('active');
          exitIntentModal.setAttribute('aria-hidden', 'false');
          document.body.style.overflow = 'hidden';
        }
      }
    }

    if (sessionStorage.getItem('vk_exit_intent_shown') !== '1') {
      document.addEventListener('mouseleave', handleExitIntent);
    }

    if (exitIntentDonateBtn) {
      exitIntentDonateBtn.addEventListener('click', () => {
        exitIntentModal.classList.remove('active');
        exitIntentModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        openModal('donate-modal');
      });
    }

    if (exitIntentDismissBtn) {
      exitIntentDismissBtn.addEventListener('click', () => {
        exitIntentModal.classList.remove('active');
        exitIntentModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
      });
    }

    exitIntentModal.addEventListener('click', (e) => {
      if (e.target === exitIntentModal) {
        exitIntentModal.classList.remove('active');
        exitIntentModal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
      }
    });
  }

  // ==========================================================================
  // 8. CRO: MOBILE STICKY BOTTOM CTA BAR (INTERSECTION & SCROLL POSITION AWARE)
  // ==========================================================================
  const mobileStickyBar = document.getElementById('vk-mobile-sticky-bar');
  const inPageMainCtaBtn = document.querySelector('.vk-cta-premium');

  if (mobileStickyBar) {
    function hasScrolledPastMainBtn() {
      if (!inPageMainCtaBtn) return false;
      const rect = inPageMainCtaBtn.getBoundingClientRect();
      // Considered scrolled past when the button has scrolled completely above the viewport
      return rect.bottom <= 50;
    }

    function updateMobileStickyState() {
      if (window.innerWidth <= 768) {
        const isAnyModalOpen = document.querySelector(
          '.vk-modal-backdrop.active, .vk-post-donation-backdrop.active, .vk-exit-intent-backdrop.active, .bm-menu-wrap.open'
        );

        // Sticky bar ONLY appears after user scrolls past the main button and no modal is open
        const shouldShow = hasScrolledPastMainBtn() && !isAnyModalOpen;

        if (shouldShow) {
          mobileStickyBar.classList.add('visible');
          mobileStickyBar.setAttribute('aria-hidden', 'false');
        } else {
          mobileStickyBar.classList.remove('visible');
          mobileStickyBar.setAttribute('aria-hidden', 'true');
        }
      } else {
        mobileStickyBar.classList.remove('visible');
        mobileStickyBar.setAttribute('aria-hidden', 'true');
      }
    }
    window.updateMobileStickyState = updateMobileStickyState;

    if ('IntersectionObserver' in window && inPageMainCtaBtn) {
      const ctaObserver = new IntersectionObserver(() => {
        updateMobileStickyState();
      }, {
        threshold: [0, 0.1, 0.5, 1.0]
      });
      ctaObserver.observe(inPageMainCtaBtn);
    }

    window.addEventListener('scroll', updateMobileStickyState, { passive: true });
    window.addEventListener('resize', updateMobileStickyState);
    setTimeout(updateMobileStickyState, 150);

    const stickyDonateBtn = mobileStickyBar.querySelector('[data-action="donate"]');
    if (stickyDonateBtn) {
      stickyDonateBtn.addEventListener('click', () => {
        openModal('donate-modal');
      });
    }
  }

  // --- Header Elevation on Scroll ---
  const headerContainer = document.querySelector('.kAWgrd');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 10) {
      if (headerContainer) headerContainer.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.08)';
    } else {
      if (headerContainer) headerContainer.style.boxShadow = 'none';
    }
  });
});
