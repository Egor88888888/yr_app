/**
 * Enhanced Integration - Интеграция улучшений с существующей формой
 * Объединяет новые UX компоненты со старой логикой
 */

class EnhancedIntegration {
    constructor() {
        this.originalFormData = window.formData || {};
        this.isInitialized = false;
        this.animations = new Map();
        
        this.init();
    }

    /**
     * Инициализация интеграции
     */
    async init() {
        if (this.isInitialized) return;
        
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    /**
     * Настройка интеграции
     */
    setup() {
        this.enhanceCategories();
        this.enhanceFormValidation();
        this.enhanceStepTransitions();
        this.enhanceProgressIndicator();
        this.integrateTelegramWebApp();
        this.setupKeyboardNavigation();
        
        this.isInitialized = true;
        console.log('🚀 Enhanced UX integration activated');
    }

    /**
     * Улучшение категорий с анимациями
     */
    enhanceCategories() {
        const categoryContainer = document.getElementById('categories');
        if (!categoryContainer) return;

        // Добавляем поиск по категориям
        this.addCategorySearch();
        
        // Улучшаем карточки категорий
        const categoryCards = categoryContainer.querySelectorAll('.category-card');
        categoryCards.forEach((card, index) => {
            // Добавляем класс для улучшенных стилей
            card.classList.add('category-card-enhanced', 'micro-interaction');
            
            // Добавляем анимацию появления с задержкой
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);

            // Улучшенный обработчик клика
            const originalHandler = card.onclick;
            card.onclick = (e) => {
                this.handleCategorySelection(card, e);
                if (originalHandler) originalHandler.call(card, e);
            };

            // Добавляем тултип с описанием
            this.addCategoryTooltip(card);
        });
    }

    /**
     * Добавление поиска по категориям
     */
    addCategorySearch() {
        const stepContainer = document.getElementById('step-1');
        if (!stepContainer) return;

        const searchContainer = document.createElement('div');
        searchContainer.className = 'mb-6';
        searchContainer.innerHTML = `
            <div class="relative">
                <input 
                    type="text" 
                    id="category-search" 
                    placeholder="Поиск категории..." 
                    class="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                <div class="absolute inset-y-0 left-0 flex items-center pl-3">
                    <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                </div>
            </div>
        `;

        const titleElement = stepContainer.querySelector('h2');
        titleElement.parentNode.insertBefore(searchContainer, titleElement.nextSibling.nextSibling);

        // Обработчик поиска
        const searchInput = searchContainer.querySelector('#category-search');
        searchInput.addEventListener('input', (e) => {
            this.filterCategories(e.target.value);
        });
    }

    /**
     * Фильтрация категорий по поиску
     */
    filterCategories(searchTerm) {
        const categories = document.querySelectorAll('.category-card');
        const term = searchTerm.toLowerCase();

        categories.forEach(card => {
            const text = card.querySelector('.text').textContent.toLowerCase();
            const matches = text.includes(term);
            
            card.style.transition = 'all 0.3s ease';
            if (matches) {
                card.style.display = 'flex';
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            } else {
                card.style.opacity = '0.3';
                card.style.transform = 'scale(0.95)';
                if (term) {
                    setTimeout(() => {
                        if (!card.querySelector('.text').textContent.toLowerCase().includes(term)) {
                            card.style.display = 'none';
                        }
                    }, 300);
                } else {
                    card.style.display = 'flex';
                }
            }
        });
    }

    /**
     * Добавление тултипа к категории
     */
    addCategoryTooltip(card) {
        const categoryName = card.dataset.name;
        const descriptions = {
            'Семейное право': 'Развод, алименты, раздел имущества, брачные договоры',
            'Наследство': 'Вступление в наследство, завещания, наследственные споры',
            'Трудовые споры': 'Увольнение, зарплата, трудовые договоры, права работников',
            'Жилищные вопросы': 'ЖКХ, покупка-продажа недвижимости, споры с соседями',
            'Банкротство физлиц': 'Процедура банкротства, списание долгов',
            'Налоговые консультации': 'Налоговые споры, декларации, льготы',
            'Административные дела': 'Штрафы ГИБДД, административные правонарушения',
            'Арбитраж / бизнес': 'Корпоративные споры, договоры, регистрация бизнеса',
            'Защита прав потребителей': 'Возврат товаров, некачественные услуги',
            'Миграционное право': 'Гражданство, ВНЖ, РВП, миграционные споры',
            'Уголовные дела': 'Защита по уголовным делам, представительство в суде',
            'Другое': 'Другие юридические вопросы'
        };

        const description = descriptions[categoryName] || 'Подробная юридическая консультация';
        
        card.classList.add('tooltip');
        const tooltipElement = document.createElement('span');
        tooltipElement.className = 'tooltiptext';
        tooltipElement.textContent = description;
        card.appendChild(tooltipElement);
    }

    /**
     * Обработка выбора категории с анимацией
     */
    handleCategorySelection(card, event) {
        // Убираем выделение с других карточек
        document.querySelectorAll('.category-card').forEach(c => {
            c.classList.remove('selected');
        });

        // Выделяем выбранную карточку
        card.classList.add('selected');

        // Анимация пульсации
        card.style.animation = 'pulse 0.6s ease-in-out';
        
        // Эффект ripple
        this.createRippleEffect(card, event);

        setTimeout(() => {
            card.style.animation = '';
        }, 600);

        // Генерируем событие для других компонентов
        const customEvent = new CustomEvent('categorySelected', {
            detail: {
                categoryId: parseInt(card.dataset.id),
                categoryName: card.dataset.name
            }
        });
        document.dispatchEvent(customEvent);
    }

    /**
     * Создание эффекта ripple
     */
    createRippleEffect(element, event) {
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            left: ${x}px;
            top: ${y}px;
            width: ${size}px;
            height: ${size}px;
            pointer-events: none;
        `;

        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    /**
     * Улучшение валидации формы
     */
    enhanceFormValidation() {
        // Интеграция с существующими полями
        const fields = ['subcategory', 'description', 'name', 'phone', 'email', 'contact-method'];
        
        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                // Добавляем обертку для поля
                this.wrapFormField(field);
                
                // Добавляем счетчик символов для textarea
                if (field.tagName === 'TEXTAREA') {
                    this.addCharacterCounter(field);
                }
                
                // Добавляем маску для телефона
                if (fieldId === 'phone') {
                    this.addPhoneMask(field);
                }
            }
        });
    }

    /**
     * Обертка поля формы
     */
    wrapFormField(field) {
        if (field.closest('.form-field')) return; // Уже обернуто

        const wrapper = document.createElement('div');
        wrapper.className = 'form-field floating-label';
        
        field.parentNode.insertBefore(wrapper, field);
        wrapper.appendChild(field);

        // Добавляем floating label
        const label = field.previousElementSibling;
        if (label && label.tagName === 'LABEL') {
            wrapper.appendChild(label);
        }
    }

    /**
     * Добавление счетчика символов
     */
    addCharacterCounter(textarea) {
        const maxLength = 2000;
        const counter = document.createElement('div');
        counter.className = 'character-counter text-sm text-gray-500 mt-1 text-right';
        
        const updateCounter = () => {
            const length = textarea.value.length;
            counter.textContent = `${length}/${maxLength}`;
            
            if (length > maxLength * 0.9) {
                counter.classList.add('text-yellow-500');
            } else {
                counter.classList.remove('text-yellow-500');
            }
            
            if (length > maxLength) {
                counter.classList.add('text-red-500');
            } else {
                counter.classList.remove('text-red-500');
            }
        };

        textarea.addEventListener('input', updateCounter);
        textarea.parentNode.appendChild(counter);
        updateCounter();
    }

    /**
     * Добавление маски для телефона
     */
    addPhoneMask(phoneField) {
        phoneField.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            if (value.startsWith('8')) {
                value = '7' + value.slice(1);
            }
            
            if (value.startsWith('7')) {
                const formatted = value.replace(/^7(\d{3})(\d{3})(\d{2})(\d{2}).*/, '+7 ($1) $2-$3-$4');
                if (formatted !== value) {
                    e.target.value = formatted;
                }
            }
        });
    }

    /**
     * Улучшение переходов между шагами
     */
    enhanceStepTransitions() {
        // Переопределяем функции nextStep и prevStep
        const originalNextStep = window.nextStep;
        const originalPrevStep = window.prevStep;

        window.nextStep = () => {
            const currentStepEl = document.querySelector('.step:not(.hidden)');
            if (currentStepEl) {
                currentStepEl.classList.add('step-transition-exit');
            }
            
            setTimeout(() => {
                if (originalNextStep) originalNextStep();
                
                const newStepEl = document.querySelector('.step:not(.hidden)');
                if (newStepEl) {
                    newStepEl.classList.add('step-transition-enter');
                    setTimeout(() => {
                        newStepEl.classList.remove('step-transition-enter');
                        if (currentStepEl) {
                            currentStepEl.classList.remove('step-transition-exit');
                        }
                    }, 500);
                }
            }, 250);
        };

        window.prevStep = () => {
            const currentStepEl = document.querySelector('.step:not(.hidden)');
            if (currentStepEl) {
                currentStepEl.classList.add('step-transition-exit');
            }
            
            setTimeout(() => {
                if (originalPrevStep) originalPrevStep();
                
                const newStepEl = document.querySelector('.step:not(.hidden)');
                if (newStepEl) {
                    newStepEl.classList.add('step-transition-enter');
                    setTimeout(() => {
                        newStepEl.classList.remove('step-transition-enter');
                        if (currentStepEl) {
                            currentStepEl.classList.remove('step-transition-exit');
                        }
                    }, 500);
                }
            }, 250);
        };
    }

    /**
     * Улучшение индикатора прогресса
     */
    enhanceProgressIndicator() {
        const progressBar = document.getElementById('progress-bar');
        if (!progressBar) return;

        // Анимированное изменение прогресса
        const originalUpdateUI = window.updateUI;
        if (originalUpdateUI) {
            window.updateUI = function() {
                originalUpdateUI.call(this);
                
                // Добавляем анимацию к прогресс-бару
                const currentStep = window.currentStep || 1;
                const progress = (currentStep * 25);
                
                progressBar.style.transition = 'width 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            };
        }
    }

    /**
     * Интеграция с Telegram WebApp
     */
    integrateTelegramWebApp() {
        if (window.Telegram?.WebApp) {
            const tg = window.Telegram.WebApp;
            
            // Настраиваем цвета темы
            tg.setHeaderColor('#667eea');
            
            // Включаем тактильную обратную связь
            const originalHandleCategorySelection = this.handleCategorySelection;
            this.handleCategorySelection = function(card, event) {
                tg.HapticFeedback.impactOccurred('light');
                originalHandleCategorySelection.call(this, card, event);
            };

            // Обратная связь при переключении шагов
            const originalNextStep = window.nextStep;
            if (originalNextStep) {
                window.nextStep = function() {
                    tg.HapticFeedback.impactOccurred('medium');
                    originalNextStep.call(this);
                };
            }
        }
    }

    /**
     * Настройка навигации с клавиатуры
     */
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Навигация по категориям с стрелками
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                const categories = document.querySelectorAll('.category-card');
                const selected = document.querySelector('.category-card.selected');
                
                if (categories.length > 0) {
                    let currentIndex = selected ? Array.from(categories).indexOf(selected) : -1;
                    
                    if (e.key === 'ArrowRight') {
                        currentIndex = (currentIndex + 1) % categories.length;
                    } else {
                        currentIndex = currentIndex <= 0 ? categories.length - 1 : currentIndex - 1;
                    }
                    
                    categories.forEach(c => c.classList.remove('selected'));
                    categories[currentIndex].classList.add('selected');
                    categories[currentIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    e.preventDefault();
                }
            }
            
            // Enter для выбора категории
            if (e.key === 'Enter') {
                const selected = document.querySelector('.category-card.selected');
                if (selected && !selected.closest('.step.hidden')) {
                    selected.click();
                    e.preventDefault();
                }
            }
        });
    }

    /**
     * Добавление CSS анимаций
     */
    injectAnimationStyles() {
        if (document.getElementById('enhanced-animations')) return;

        const style = document.createElement('style');
        style.id = 'enhanced-animations';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
            
            .animate-fade-in {
                animation: fadeIn 0.3s ease-in-out;
            }
            
            .character-counter {
                transition: color 0.3s ease;
            }
        `;
        
        document.head.appendChild(style);
    }
}

// Автоинициализация при загрузке
let enhancedIntegration;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        enhancedIntegration = new EnhancedIntegration();
        window.enhancedIntegration = enhancedIntegration;
    });
} else {
    enhancedIntegration = new EnhancedIntegration();
    window.enhancedIntegration = enhancedIntegration;
}

// Экспорт
window.EnhancedIntegration = EnhancedIntegration; 