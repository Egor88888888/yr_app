// Admin Dashboard JavaScript - Full Functionality
class AdminDashboard {
    constructor() {
        this.currentModule = 'dashboard';
        this.data = {
            applications: [
                {
                    id: 101,
                    client: 'Иван Петров',
                    category: 'Семейное право',
                    status: 'new',
                    date: '2024-12-25',
                    description: 'Развод и раздел имущества',
                    phone: '+7 (999) 123-45-67',
                    email: 'ivan@example.com'
                },
                {
                    id: 102,
                    client: 'Мария Сидорова',
                    category: 'Трудовые споры',
                    status: 'processing',
                    date: '2024-12-24',
                    description: 'Незаконное увольнение',
                    phone: '+7 (999) 987-65-43',
                    email: 'maria@example.com'
                }
            ],
            clients: [
                {
                    id: 1,
                    name: 'Иван Петров',
                    phone: '+7 (999) 123-45-67',
                    email: 'ivan@example.com',
                    applications: 2,
                    totalPaid: 15000
                }
            ],
            payments: [
                {
                    id: 1,
                    client: 'Иван Петров',
                    amount: 5000,
                    status: 'paid',
                    date: '2024-12-25'
                }
            ],
            stats: {
                newApplications: 12,
                totalClients: 347,
                monthlyRevenue: 147500,
                conversion: 23.4
            }
        };
        this.init();
    }

    init() {
        this.renderDashboard();
    }

    renderDashboard() {
        this.updateStats();
        this.renderRecentApplications();
    }

    updateStats() {
        const stats = this.data.stats;
        document.getElementById('stat-new-apps').textContent = stats.newApplications;
        document.getElementById('stat-total-clients').textContent = stats.totalClients;
        document.getElementById('stat-revenue').textContent = `₽${stats.monthlyRevenue.toLocaleString()}`;
        document.getElementById('stat-conversion').textContent = `${stats.conversion}%`;
    }

    renderRecentApplications() {
        const container = document.getElementById('recent-applications');
        const recent = this.data.applications.slice(0, 3);
        
        container.innerHTML = recent.map(app => `
            <div class="glass-dark rounded-lg p-4 card-hover cursor-pointer" onclick="adminDashboard.viewApplication(${app.id})">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="text-white font-medium">#${app.id} ${app.category}</p>
                        <p class="text-white opacity-75 text-sm">${app.client}</p>
                    </div>
                    <span class="text-sm ${this.getStatusColor(app.status)}">${this.getStatusText(app.status)}</span>
                </div>
            </div>
        `).join('');
    }

    renderApplications() {
        const container = document.getElementById('applications-table');
        container.innerHTML = this.data.applications.map(app => `
            <tr class="border-b border-white border-opacity-20 hover:bg-white hover:bg-opacity-10 cursor-pointer">
                <td class="px-6 py-4">#${app.id}</td>
                <td class="px-6 py-4">${app.client}</td>
                <td class="px-6 py-4">${app.category}</td>
                <td class="px-6 py-4">
                    <span class="px-2 py-1 rounded text-xs ${this.getStatusColor(app.status)}">${this.getStatusText(app.status)}</span>
                </td>
                <td class="px-6 py-4">${this.formatDate(app.date)}</td>
                <td class="px-6 py-4">
                    <button onclick="adminDashboard.viewApplication(${app.id})" class="btn-glass px-3 py-1 rounded text-sm">Открыть</button>
                </td>
            </tr>
        `).join('');
    }

    getStatusColor(status) {
        const colors = {
            'new': 'text-green-300',
            'processing': 'text-yellow-300',
            'completed': 'text-blue-300'
        };
        return colors[status] || 'text-gray-300';
    }

    getStatusText(status) {
        const texts = {
            'new': 'Новая',
            'processing': 'В работе',
            'completed': 'Завершена'
        };
        return texts[status] || status;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU');
    }

    viewApplication(id) {
        const app = this.data.applications.find(a => a.id === id);
        if (!app) return;

        this.showModal(`
            <div class="text-white">
                <h2 class="text-2xl font-bold mb-6">Заявка #${app.id}</h2>
                <div class="space-y-4">
                    <p><strong>Клиент:</strong> ${app.client}</p>
                    <p><strong>Категория:</strong> ${app.category}</p>
                    <p><strong>Статус:</strong> ${this.getStatusText(app.status)}</p>
                    <p><strong>Описание:</strong> ${app.description}</p>
                </div>
                <button onclick="adminDashboard.hideModal()" class="btn-glass px-6 py-2 rounded-lg mt-6">Закрыть</button>
            </div>
        `);
    }

    showModal(content) {
        document.getElementById('modal-content').innerHTML = content;
        document.getElementById('modal-overlay').classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }
}

// Module switching
function showModule(moduleName) {
    document.querySelectorAll('.module').forEach(module => {
        module.classList.add('hidden');
    });
    
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('sidebar-active');
    });
    
    document.getElementById(`module-${moduleName}`).classList.remove('hidden');
    document.getElementById(`nav-${moduleName}`).classList.add('sidebar-active');
    
    if (moduleName === 'applications') {
        adminDashboard.renderApplications();
    }
}

function createApplication() {
    alert('Переход к форме создания заявки');
}

function applyFilters() {
    alert('Применение фильтров');
}

function logout() {
    if (confirm('Выйти?')) {
        window.location.href = '/';
    }
}

function createClient() {
    adminDashboard.showModal(`
        <div class="text-white">
            <h2 class="text-2xl font-bold mb-6">Добавить нового клиента</h2>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Имя и фамилия</label>
                    <input type="text" id="client-name" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="Иван Петров">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Телефон</label>
                    <input type="tel" id="client-phone" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="+7 (999) 123-45-67">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Email</label>
                    <input type="email" id="client-email" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="email@example.com">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Примечания</label>
                    <textarea id="client-notes" rows="3" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="Дополнительная информация о клиенте"></textarea>
                </div>
            </div>
            
            <div class="flex gap-4 mt-8">
                <button onclick="saveClient()" class="btn-glass px-6 py-2 rounded-lg bg-green-600">Сохранить</button>
                <button onclick="adminDashboard.hideModal()" class="btn-glass px-6 py-2 rounded-lg">Отмена</button>
            </div>
        </div>
    `);
}

function createPayment() {
    adminDashboard.showModal(`
        <div class="text-white">
            <h2 class="text-2xl font-bold mb-6">Выставить счет</h2>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Клиент</label>
                    <select id="payment-client" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent">
                        <option value="">Выберите клиента</option>
                        <option value="1">Иван Петров</option>
                        <option value="2">Мария Сидорова</option>
                        <option value="3">Алексей Козлов</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Услуга</label>
                    <select id="payment-service" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent">
                        <option value="">Выберите услугу</option>
                        <option value="consultation">Консультация юриста - ₽5,000</option>
                        <option value="documents">Подготовка документов - ₽8,000</option>
                        <option value="representation">Представительство в суде - ₽15,000</option>
                        <option value="custom">Другое (укажите сумму)</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Сумма (₽)</label>
                    <input type="number" id="payment-amount" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="5000">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Описание</label>
                    <textarea id="payment-description" rows="3" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="Описание услуги..."></textarea>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Срок оплаты</label>
                    <select id="payment-deadline" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent">
                        <option value="immediately">Немедленно</option>
                        <option value="3days">3 дня</option>
                        <option value="week">1 неделя</option>
                        <option value="month">1 месяц</option>
                    </select>
                </div>
            </div>
            
            <div class="flex gap-4 mt-8">
                <button onclick="savePayment()" class="btn-glass px-6 py-2 rounded-lg bg-green-600">Выставить счет</button>
                <button onclick="adminDashboard.hideModal()" class="btn-glass px-6 py-2 rounded-lg">Отмена</button>
            </div>
        </div>
    `);
}

function createAdmin() {
    adminDashboard.showModal(`
        <div class="text-white">
            <h2 class="text-2xl font-bold mb-6">Добавить администратора</h2>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Имя и фамилия</label>
                    <input type="text" id="admin-name" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="Анна Иванова">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Email</label>
                    <input type="email" id="admin-email" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="admin@lawcenter.ru">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Telegram ID</label>
                    <input type="text" id="admin-telegram" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent" placeholder="@username или ID">
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Роль</label>
                    <select id="admin-role" class="glass-dark w-full rounded-lg px-4 py-2 text-white bg-transparent">
                        <option value="">Выберите роль</option>
                        <option value="operator">Оператор - просмотр заявок</option>
                        <option value="lawyer">Юрист - обработка заявок</option>
                        <option value="manager">Менеджер - управление клиентами</option>
                        <option value="admin">Администратор - полные права</option>
                    </select>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-2">Права доступа</label>
                    <div class="space-y-2">
                        <label class="flex items-center">
                            <input type="checkbox" id="perm-applications" class="mr-2">
                            <span class="text-sm">Управление заявками</span>
                        </label>
                        <label class="flex items-center">
                            <input type="checkbox" id="perm-clients" class="mr-2">
                            <span class="text-sm">Управление клиентами</span>
                        </label>
                        <label class="flex items-center">
                            <input type="checkbox" id="perm-payments" class="mr-2">
                            <span class="text-sm">Управление платежами</span>
                        </label>
                        <label class="flex items-center">
                            <input type="checkbox" id="perm-analytics" class="mr-2">
                            <span class="text-sm">Просмотр аналитики</span>
                        </label>
                    </div>
                </div>
            </div>
            
            <div class="flex gap-4 mt-8">
                <button onclick="saveAdmin()" class="btn-glass px-6 py-2 rounded-lg bg-green-600">Добавить админа</button>
                <button onclick="adminDashboard.hideModal()" class="btn-glass px-6 py-2 rounded-lg">Отмена</button>
            </div>
        </div>
    `);
}

function saveClient() {
    const name = document.getElementById('client-name').value;
    const phone = document.getElementById('client-phone').value;
    const email = document.getElementById('client-email').value;
    const notes = document.getElementById('client-notes').value;
    
    if (!name || !phone) {
        alert('Заполните обязательные поля: имя и телефон');
        return;
    }
    
    // Симуляция сохранения
    alert(`✅ Клиент "${name}" успешно добавлен!`);
    adminDashboard.hideModal();
    
    // Обновляем список клиентов
    showModule('clients');
}

function savePayment() {
    const client = document.getElementById('payment-client').value;
    const service = document.getElementById('payment-service').value;
    const amount = document.getElementById('payment-amount').value;
    const description = document.getElementById('payment-description').value;
    
    if (!client || !amount) {
        alert('Заполните обязательные поля: клиент и сумма');
        return;
    }
    
    // Симуляция создания платежа
    alert(`✅ Счет на сумму ₽${amount} выставлен клиенту!`);
    adminDashboard.hideModal();
    
    // Обновляем модуль платежей
    showModule('payments');
}

function saveAdmin() {
    const name = document.getElementById('admin-name').value;
    const email = document.getElementById('admin-email').value;
    const telegram = document.getElementById('admin-telegram').value;
    const role = document.getElementById('admin-role').value;
    
    if (!name || !email || !role) {
        alert('Заполните обязательные поля');
        return;
    }
    
    // Симуляция добавления админа
    alert(`✅ Администратор "${name}" с ролью "${role}" добавлен!`);
    adminDashboard.hideModal();
    
    // Обновляем модуль админов
    showModule('admin-users');
}

// Initialize
let adminDashboard;
document.addEventListener('DOMContentLoaded', () => {
    adminDashboard = new AdminDashboard();
    
    document.getElementById('modal-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) {
            adminDashboard.hideModal();
        }
    });
});
