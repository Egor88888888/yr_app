/*
=======================================================
🚀 КОМПАКТНАЯ УЛЬТРА-СОВРЕМЕННАЯ СИСТЕМА
=======================================================
Оптимизированная для экрана без прокрутки
*/

'use strict';

// Telegram WebApp Integration
const tg = window.Telegram?.WebApp || {
    initDataUnsafe: {},
    initData: '',
    MainButton: { show(){}, hide(){}, setText(){}, onClick(){} },
    BackButton: { show(){}, hide(){}, onClick(){} },
    HapticFeedback: { 
        impactOccurred(){}, 
        notificationOccurred(){}, 
        selectionChanged(){} 
    },
    close() { window.close(); },
    ready() {},
    expand() {}
};

tg.ready();
tg.expand?.();

// Компактные категории
const CATEGORIES = [
    { id: 1, name: "Семейное", icon: "👨‍👩‍👧‍👦" },
    { id: 2, name: "Бизнес", icon: "🏢" },
    { id: 3, name: "Недвижимость", icon: "🏠" },
    { id: 4, name: "Трудовое", icon: "💼" },
    { id: 5, name: "Налоговое", icon: "💰" },
    { id: 6, name: "Админ.", icon: "📋" },
    { id: 7, name: "Уголовное", icon: "⚖️" },
    { id: 8, name: "Гражданское", icon: "📝" },
    { id: 9, name: "IP", icon: "💡" },
    { id: 10, name: "Миграция", icon: "✈️" },
    { id: 11, name: "Банкротство", icon: "🛡️" },
    { id: 12, name: "Другое", icon: "🔄" }
];

// Компактное приложение
class CompactApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {
            category_id: null,
            category_name: "",
            subcategory: "",
            description: "",
            name: "",
            phone: "",
            email: "",
            contact_method: "",
            contact_time: "any",
            files: []
        };
        this.init();
    }

    init() {
        this.renderCategories();
        this.setupEvents();
        this.updateUI();
    }

    setupEvents() {
        // Навигация
        document.getElementById('back-btn')?.addEventListener('click', () => this.prevStep());
        document.getElementById('next-btn')?.addEventListener('click', () => this.nextStep());
        
        // Форма
        document.addEventListener('input', (e) => {
            if (this.formData.hasOwnProperty(e.target.id)) {
                this.formData[e.target.id] = e.target.value;
                this.validate();
            }
        });
        
        // Счетчик символов
        document.getElementById('description')?.addEventListener('input', (e) => {
            const counter = document.getElementById('description-counter');
            if (counter) counter.textContent = e.target.value.length;
        });
        
        // Файлы
        document.getElementById('files')?.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }

    renderCategories() {
        const container = document.getElementById('categories');
        if (!container) return;

        container.innerHTML = CATEGORIES.map(cat => `
            <div class="ultra-category" 
                 data-id="${cat.id}" 
                 onclick="app.selectCategory(${cat.id}, '${cat.name}')">
                <div class="ultra-category-emoji">${cat.icon}</div>
                <div class="ultra-category-text">${cat.name}</div>
            </div>
        `).join('');
    }

    selectCategory(id, name) {
        // Убрать предыдущее выделение
        document.querySelectorAll('.ultra-category').forEach(el => 
            el.classList.remove('selected'));
        
        // Выделить новую категорию
        document.querySelector(`[data-id="${id}"]`)?.classList.add('selected');
        
        this.formData.category_id = id;
        this.formData.category_name = name;
        
        // Показать выбор
        const selectedDiv = document.getElementById('selected-category');
        const selectedName = document.getElementById('selected-category-name');
        if (selectedDiv && selectedName) {
            selectedName.textContent = name;
            selectedDiv.classList.remove('hidden');
        }
        
        this.validate();
        tg.HapticFeedback?.selectionChanged();
    }

    handleFiles(files) {
        const fileList = document.getElementById('file-list');
        if (!fileList || !files.length) return;

        Array.from(files).slice(0, 5).forEach(file => {
            if (file.size > 10 * 1024 * 1024) return; // 10MB limit
            
            const fileDiv = document.createElement('div');
            fileDiv.style.cssText = `
                display: flex; 
                align-items: center; 
                gap: 8px; 
                padding: 8px; 
                background: #f8f9fa; 
                border-radius: 8px; 
                margin-bottom: 8px;
                font-size: 12px;
            `;
            
            fileDiv.innerHTML = `
                <span>📄</span>
                <span>${file.name}</span>
                <span style="margin-left: auto; color: #666;">
                    ${(file.size / 1024).toFixed(0)}KB
                </span>
            `;
            
            fileList.appendChild(fileDiv);
            this.formData.files.push(file);
        });
    }

    validate() {
        const nextBtn = document.getElementById('next-btn');
        if (!nextBtn) return;

        let isValid = false;
        
        switch (this.currentStep) {
            case 1:
                isValid = !!this.formData.category_id;
                break;
            case 2:
                isValid = this.formData.description.length > 10;
                break;
            case 3:
                isValid = this.formData.name && 
                         this.formData.phone && 
                         this.formData.contact_method;
                break;
            case 4:
                isValid = true;
                break;
        }
        
        nextBtn.disabled = !isValid;
        nextBtn.style.opacity = isValid ? '1' : '0.5';
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateUI();
            tg.HapticFeedback?.impactOccurred('light');
        }
    }

    nextStep() {
        if (this.currentStep === 4) {
            this.submit();
            return;
        }
        
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateUI();
            tg.HapticFeedback?.impactOccurred('light');
        }
    }

    updateUI() {
        // Скрыть все шаги
        document.querySelectorAll('.ultra-step').forEach(step => {
            step.classList.remove('active');
            step.classList.add('hidden');
        });
        
        // Показать текущий шаг
        const currentStepEl = document.getElementById(`step-${this.currentStep}`);
        if (currentStepEl) {
            currentStepEl.classList.add('active');
            currentStepEl.classList.remove('hidden');
        }
        
        // Обновить индикатор
        const indicator = document.getElementById('step-indicator');
        if (indicator) {
            indicator.textContent = `Шаг ${this.currentStep} из ${this.totalSteps}`;
        }
        
        // Обновить прогресс
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${(this.currentStep / this.totalSteps) * 100}%`;
        }
        
        // Кнопки навигации
        const backBtn = document.getElementById('back-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (backBtn) {
            backBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
        }
        
        if (nextBtn) {
            nextBtn.textContent = this.currentStep === 4 ? 'Отправить' : 'Продолжить →';
        }
        
        // Заполнить данные для проверки
        if (this.currentStep === 4) {
            this.renderReview();
        }
        
        this.validate();
    }

    renderReview() {
        const reviewContent = document.getElementById('review-content');
        if (!reviewContent) return;
        
        const categoryName = this.formData.category_name || 'Не выбрано';
        const contactMethod = this.formData.contact_method ? 
            {'telegram': '💬 Telegram', 'phone': '📞 Звонок', 'whatsapp': '💚 WhatsApp', 'email': '📧 Email'}[this.formData.contact_method] : 
            'Не выбрано';
        
        reviewContent.innerHTML = `
            <div style="background: #f8f9fa; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                <div style="font-weight: 600; margin-bottom: 8px;">📋 Категория:</div>
                <div style="color: #666; margin-bottom: 12px;">${categoryName}</div>
                
                <div style="font-weight: 600; margin-bottom: 8px;">👤 Контакты:</div>
                <div style="color: #666; margin-bottom: 4px;">${this.formData.name}</div>
                <div style="color: #666; margin-bottom: 4px;">${this.formData.phone}</div>
                <div style="color: #666; margin-bottom: 12px;">${contactMethod}</div>
                
                ${this.formData.description ? `
                    <div style="font-weight: 600; margin-bottom: 8px;">📝 Описание:</div>
                    <div style="color: #666; font-size: 14px;">${this.formData.description.substring(0, 100)}${this.formData.description.length > 100 ? '...' : ''}</div>
                ` : ''}
            </div>
        `;
    }

    async submit() {
        const nextBtn = document.getElementById('next-btn');
        if (!nextBtn) return;
        
        nextBtn.textContent = 'Отправляем...';
        nextBtn.disabled = true;
        
        try {
            const response = await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...this.formData,
                    tg_user_id: tg.initDataUnsafe?.user?.id,
                    tg_username: tg.initDataUnsafe?.user?.username
                })
            });
            
            if (response.ok) {
                this.showSuccess();
                tg.HapticFeedback?.notificationOccurred('success');
            } else {
                throw new Error('Ошибка отправки');
            }
        } catch (error) {
            console.error('Submit error:', error);
            nextBtn.textContent = 'Повторить';
            nextBtn.disabled = false;
            tg.HapticFeedback?.notificationOccurred('error');
        }
    }

    showSuccess() {
        // Скрыть все шаги
        document.querySelectorAll('.ultra-step').forEach(step => {
            step.classList.add('hidden');
        });
        
        // Показать успех
        const successStep = document.getElementById('success');
        if (successStep) {
            successStep.classList.remove('hidden');
        }
        
        // Скрыть навигацию
        const navigation = document.querySelector('.ultra-navigation');
        if (navigation) {
            navigation.style.display = 'none';
        }
    }
}

// Инициализация
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new CompactApp();
    window.app = app; // Для доступа из HTML
});

// CSS анимация для ripple эффекта
if (!document.getElementById('premium-styles')) {
    const style = document.createElement('style');
    style.id = 'premium-styles';
    style.textContent = `
        @keyframes premiumRipple {
            to { transform: scale(4); opacity: 0; }
        }
        .ultra-step { 
            transition: all 0.3s ease; 
        }
        .ultra-step.active { 
            animation: fadeInUp 0.4s ease; 
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
}