/*
=======================================================
🔧 ПРОСТАЯ ТЕСТОВАЯ ВЕРСИЯ ДЛЯ ОТЛАДКИ
=======================================================
*/

'use strict';

// Простые данные
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

// Глобальные переменные
window.currentStep = 1;
window.formData = {
    category_id: null,
    category_name: "",
    subcategory: "",
    description: "",
    name: "",
    phone: "",
    email: "",
    contact_method: "",
    contact_time: "any"
};

// Простая валидация
function validateStep() {
    console.log('🔍 Validating step:', window.currentStep);
    
    const nextBtn = document.getElementById('next-btn');
    if (!nextBtn) {
        console.error('❌ Next button not found!');
        return;
    }
    
    let isValid = false;
    
    switch (window.currentStep) {
        case 1:
            isValid = !!window.formData.category_id;
            console.log('Step 1 - Category selected:', window.formData.category_id, 'Valid:', isValid);
            break;
            
        case 2:
            const desc = window.formData.description || '';
            isValid = desc.trim().length >= 3; // Снижаем требование до 3 символов
            console.log('Step 2 - Description:', `"${desc}"`, 'Length:', desc.trim().length, 'Valid:', isValid);
            break;
            
        case 3:
            isValid = window.formData.name.trim() && 
                     window.formData.phone.trim() && 
                     window.formData.contact_method;
            console.log('Step 3 - All fields:', {
                name: window.formData.name.trim(),
                phone: window.formData.phone.trim(), 
                contact: window.formData.contact_method
            }, 'Valid:', isValid);
            break;
            
        case 4:
            isValid = true;
            break;
    }
    
    // Применяем валидацию
    nextBtn.disabled = !isValid;
    nextBtn.style.opacity = isValid ? '1' : '0.5';
    nextBtn.style.pointerEvents = isValid ? 'auto' : 'none';
    nextBtn.style.cursor = isValid ? 'pointer' : 'not-allowed';
    
    console.log('✅ Button updated:', {
        disabled: nextBtn.disabled,
        opacity: nextBtn.style.opacity,
        pointerEvents: nextBtn.style.pointerEvents
    });
}

// Обновление UI
function updateUI() {
    console.log('🔄 Updating UI for step:', window.currentStep);
    
    // Скрыть все шаги
    document.querySelectorAll('.ultra-step').forEach(step => {
        step.classList.remove('active');
        step.classList.add('hidden');
    });
    
    // Показать текущий шаг
    const currentStepEl = document.getElementById(`step-${window.currentStep}`);
    if (currentStepEl) {
        currentStepEl.classList.add('active');
        currentStepEl.classList.remove('hidden');
    }
    
    // Обновить индикатор
    const indicator = document.getElementById('step-indicator');
    if (indicator) {
        indicator.textContent = `Шаг ${window.currentStep} из 4`;
    }
    
    // Обновить прогресс
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
        progressBar.style.width = `${(window.currentStep / 4) * 100}%`;
    }
    
    // Кнопки навигации
    const backBtn = document.getElementById('back-btn');
    const nextBtn = document.getElementById('next-btn');
    
    if (backBtn) {
        backBtn.style.display = window.currentStep > 1 ? 'block' : 'none';
    }
    
    if (nextBtn) {
        nextBtn.textContent = window.currentStep === 4 ? 'Отправить' : 'Продолжить →';
    }
    
    // Валидация
    validateStep();
}

// Навигация
function nextStep() {
    console.log('➡️ Next step clicked from step:', window.currentStep);
    
    if (window.currentStep === 4) {
        submitForm();
        return;
    }
    
    if (window.currentStep < 4) {
        window.currentStep++;
        updateUI();
    }
}

function prevStep() {
    console.log('⬅️ Previous step clicked from step:', window.currentStep);
    
    if (window.currentStep > 1) {
        window.currentStep--;
        updateUI();
    }
}

// Выбор категории
function selectCategory(id, name) {
    console.log('📋 Category selected:', id, name);
    
    // Убрать предыдущее выделение
    document.querySelectorAll('.ultra-category').forEach(el => 
        el.classList.remove('selected'));
    
    // Выделить новую категорию
    document.querySelector(`[data-id="${id}"]`)?.classList.add('selected');
    
    window.formData.category_id = id;
    window.formData.category_name = name;
    
    // Показать выбор
    const selectedDiv = document.getElementById('selected-category');
    const selectedName = document.getElementById('selected-category-name');
    if (selectedDiv && selectedName) {
        selectedName.textContent = name;
        selectedDiv.classList.remove('hidden');
    }
    
    validateStep();
}

// Отправка формы
async function submitForm() {
    console.log('📤 Submitting form:', window.formData);
    
    const nextBtn = document.getElementById('next-btn');
    nextBtn.textContent = 'Отправляем...';
    nextBtn.disabled = true;
    
    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(window.formData)
        });
        
        if (response.ok) {
            showSuccess();
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('❌ Submit error:', error);
        alert(`Ошибка отправки: ${error.message}`);
        nextBtn.textContent = 'Повторить';
        nextBtn.disabled = false;
    }
}

// Показать успех
function showSuccess() {
    document.querySelectorAll('.ultra-step').forEach(step => step.classList.add('hidden'));
    document.getElementById('success')?.classList.remove('hidden');
    document.querySelector('.ultra-navigation').style.display = 'none';
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Simple app starting...');
    
    // Рендер категорий
    const container = document.getElementById('categories');
    if (container) {
        container.innerHTML = CATEGORIES.map(cat => `
            <div class="ultra-category" 
                 data-id="${cat.id}" 
                 onclick="selectCategory(${cat.id}, '${cat.name}')">
                <div class="ultra-category-emoji">${cat.icon}</div>
                <div class="ultra-category-text">${cat.name}</div>
            </div>
        `).join('');
    }
    
    // События навигации
    document.getElementById('back-btn')?.addEventListener('click', prevStep);
    document.getElementById('next-btn')?.addEventListener('click', nextStep);
    
    // События полей
    document.getElementById('description')?.addEventListener('input', (e) => {
        window.formData.description = e.target.value;
        
        const counter = document.getElementById('description-counter');
        if (counter) counter.textContent = e.target.value.length;
        
        console.log('📝 Description updated:', `"${e.target.value}"`);
        validateStep();
    });
    
    document.getElementById('subcategory')?.addEventListener('input', (e) => {
        window.formData.subcategory = e.target.value;
        validateStep();
    });
    
    document.getElementById('name')?.addEventListener('input', (e) => {
        window.formData.name = e.target.value;
        validateStep();
    });
    
    document.getElementById('phone')?.addEventListener('input', (e) => {
        window.formData.phone = e.target.value;
        validateStep();
    });
    
    document.getElementById('email')?.addEventListener('input', (e) => {
        window.formData.email = e.target.value;
        validateStep();
    });
    
    document.getElementById('contact-method')?.addEventListener('change', (e) => {
        window.formData.contact_method = e.target.value;
        validateStep();
    });
    
    document.getElementById('contact-time')?.addEventListener('change', (e) => {
        window.formData.contact_time = e.target.value;
        validateStep();
    });
    
    // Инициальная настройка
    updateUI();
    
    console.log('✅ Simple app initialized');
});

// Глобальные функции для HTML
window.selectCategory = selectCategory;
window.nextStep = nextStep;
window.prevStep = prevStep;