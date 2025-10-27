document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeImagePreview();
    initializeFormValidation();
    initializeTableFeatures();
    initializeCharts();
    initializeAnimations();
    initializeKeyboardShortcuts();
});


function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeImagePreview() {
    const imageInput = document.getElementById('imagem');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    let preview = document.getElementById('image-preview');
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = 'image-preview';
                        preview.className = 'image-preview mt-3 rounded shadow';
                        preview.style.maxWidth = '200px';
                        preview.style.maxHeight = '200px';
                        imageInput.parentNode.appendChild(preview);
                    }
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Mostrar primeiro campo inválido
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstInvalid.focus();
                }
            }
            form.classList.add('was-validated');
        });
    });

    // Validação customizada para quantidade
    const quantidadeInput = document.getElementById('quantidade');
    if (quantidadeInput) {
        quantidadeInput.addEventListener('input', function() {
            const value = parseInt(this.value);
            if (value <= 0 || isNaN(value)) {
                this.setCustomValidity('A quantidade deve ser maior que zero');
            } else {
                this.setCustomValidity('');
            }
        });
    }

    // Feedback visual em tempo real
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.checkValidity()) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });
}

function initializeTableFeatures() {
    // Busca em tempo real na tabela
    const searchInput = document.getElementById('table-search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            let visibleCount = 0;
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Atualizar contador
            const counter = document.getElementById('visible-count');
            if (counter) {
                counter.textContent = visibleCount;
            }
        }, 300));
    }

    // Ordenação de colunas
    const sortableHeaders = document.querySelectorAll('th[data-sort]');
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const sortBy = this.dataset.sort;
            const isAsc = this.classList.contains('sort-asc');
            sortTable(sortBy, !isAsc);
        });
    });
}

// Na função initializeCharts(), substitua a parte do condicaoChart por:
function initializeCharts() {
    // Gráfico de condições no dashboard
    const condicaoChart = document.getElementById('condicaoChart');
    if (condicaoChart && typeof Chart !== 'undefined') {
        const ctx = condicaoChart.getContext('2d');
        
        // Buscar dados reais da API
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                const cores = {
                    'Ótimo': '#198754',
                    'Bom': '#0dcaf0', 
                    'Recuperável': '#ffc107',
                    'Péssimo': '#dc3545'
                };
                
                const labels = [];
                const valores = [];
                const coresArray = [];
                
                // Organizar dados na ordem correta
                const ordem = ['Ótimo', 'Bom', 'Recuperável', 'Péssimo'];
                ordem.forEach(condicao => {
                    const item = data.condicoes.find(c => c.condicao === condicao);
                    labels.push(condicao);
                    valores.push(item ? item.count : 0);
                    coresArray.push(cores[condicao]);
                });
                
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: valores,
                            backgroundColor: coresArray,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 20,
                                    usePointStyle: true,
                                    font: { size: 11 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.raw || 0;
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                        return `${label}: ${value} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        cutout: '60%'
                    }
                });
            })
            .catch(error => {
                console.error('Erro ao carregar dados do gráfico:', error);
                // Fallback para dados mockados
                const chartData = {
                    labels: ['Ótimo', 'Bom', 'Recuperável', 'Péssimo'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#198754', '#0dcaf0', '#ffc107', '#dc3545'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                };
                
                new Chart(ctx, {
                    type: 'doughnut',
                    data: chartData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' }
                        },
                        cutout: '60%'
                    }
                });
            });
    }
}


function initializeAnimations() {
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

   
    document.querySelectorAll('.card, .stats-card, .table-responsive').forEach(el => {
        observer.observe(el);
    });

   
    const statsNumbers = document.querySelectorAll('.stats-number');
    statsNumbers.forEach(numberEl => {
        const finalValue = parseInt(numberEl.textContent);
        if (!isNaN(finalValue)) {
            animateCounter(numberEl, finalValue);
        }
    });
}

function initializeChat() {
    const chatToggle = document.getElementById('chatToggle');
    const chatModal = new bootstrap.Modal(document.getElementById('chatModal'));
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    const chatMessages = document.getElementById('chatMessages');

    chatToggle.addEventListener('click', () => {
        chatModal.show();
        chatInput.focus();
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    sendButton.addEventListener('click', sendMessage);

    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage('user', message);
        chatInput.value = '';

        showTypingIndicator();

        fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator();
            if (data.error) {
                addMessage('ai', `Erro: ${data.error}`);
            } else {
                addMessage('ai', data.response);
            }
        })
        .catch(error => {
            removeTypingIndicator();
            addMessage('ai', 'Erro de conexão');
            console.error('Erro no chat:', error);
        });
    }

    function addMessage(sender, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message message-${sender}`;
    
    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = sender === 'user' ? 'Você' : 'Assistente';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    
    if (sender === 'ai') {
        content.innerHTML = text;  
    } else {
        content.textContent = text;
    }
    
    messageDiv.appendChild(header);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typingIndicator';
        typingDiv.className = 'chat-message message-ai typing-indicator';
        typingDiv.innerHTML = '<div class="message-header">Assistente</div>Pensando<div class="typing-dots"><span></span><span></span><span></span></div>';
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    setTimeout(() => {
        if (chatMessages.children.length === 0) {
            addMessage('ai', 'Olá! Sou seu assistente de patrimônio escolar. Como posso ajudar você hoje?');
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeImagePreview();
    initializeFormValidation();
    initializeTableFeatures();
    initializeCharts();
    initializeAnimations();
    initializeKeyboardShortcuts();
    initializeChat();
});

function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('table-search') || document.querySelector('input[type="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            const newBtn = document.querySelector('a[href*="cadastro"]');
            if (newBtn) {
                window.location.href = newBtn.href;
            }
        }
        
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
}

// Funções utilitárias
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function animateCounter(element, finalValue, duration = 2000) {
    const startValue = 0;
    const startTime = performance.now();
    
    function updateCounter(currentTime) {
        const elapsedTime = currentTime - startTime;
        const progress = Math.min(elapsedTime / duration, 1);
        
        const currentValue = Math.floor(progress * finalValue);
        element.textContent = currentValue.toLocaleString('pt-BR');
        
        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = finalValue.toLocaleString('pt-BR');
        }
    }
    
    requestAnimationFrame(updateCounter);
}

function showLoading(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processando...';
    button.disabled = true;
    
    return function() {
        button.innerHTML = originalText;
        button.disabled = false;
    };
}

function showNotification(message, type = 'info', duration = 5000) {
    // Remove notificação existente
    const existingAlert = document.querySelector('.alert-notification');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-notification alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remover após duração
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, duration);
}

// Exportar dados da tabela
function exportTableToCSV(filename = 'patrimonios.csv') {
    const table = document.querySelector('table');
    if (!table) return;
    
    const rows = Array.from(table.querySelectorAll('tr'));
    const csvContent = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => {
            // Remover ícones e elementos HTML
            const text = cell.textContent.replace(/[\n\r]+|[\s]{2,}/g, ' ').trim();
            return `"${text.replace(/"/g, '""')}"`;
        }).join(',');
    }).join('\n');
    
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}


// Service Worker para funcionalidade offline
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('ServiceWorker registrado com sucesso: ', registration.scope);
            })
            .catch(error => {
                console.log('Falha ao registrar ServiceWorker: ', error);
            });
    });

    
}
