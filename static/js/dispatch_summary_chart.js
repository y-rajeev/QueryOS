// static/js/dispatch_summary_chart.js

document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('distributionChart').getContext('2d');
    const chartCanvas = document.getElementById('distributionChart');
    const karurPercentage = parseFloat(chartCanvas.dataset.karurPercentage);
    const mumbaiPercentage = parseFloat(chartCanvas.dataset.mumbaiPercentage);

    const chartData = {
        type: 'doughnut',
        data: {
            labels: ['Karur', 'Mumbai'],
            datasets: [{
                data: [karurPercentage, mumbaiPercentage],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(255, 99, 132, 0.5)'
                ],
                borderColor: [
                    'rgb(75, 192, 192)',
                    'rgb(255, 99, 132)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.raw + '%';
                        }
                    }
                }
            }
        }
    };

    new Chart(ctx, chartData);
}); 