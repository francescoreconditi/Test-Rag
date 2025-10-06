# Dashboard Dark Mode + Excel/CSV Export Updates

## Completed Files (4/7)
- ✅ revenue.html
- ✅ cost_center.html
- ✅ executive.html
- ✅ salesforce.html

## Remaining Files (3/7)
- ⏳ production.html (SheetJS library added, needs export functions)
- ⏳ cashflow.html
- ⏳ scad.html

## Updates Required for Each File

### Step 1: Add SheetJS Library (in `<head>` section)
Add after Chart.js script tag:
```html
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
```

### Step 2: Add Dark Mode CSS (in `<style>` section)
Add after existing material-card styles:
```css
.ripple { position: relative; overflow: hidden; }
.ripple:active::after {
    content: ""; position: absolute; top: 50%; left: 50%; width: 100%; height: 100%;
    background: rgba(255,255,255,0.3); border-radius: 50%;
    transform: translate(-50%, -50%) scale(0); animation: ripple-animation 0.6s ease-out;
}
@keyframes ripple-animation { to { transform: translate(-50%, -50%) scale(2); opacity: 0; } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
.animate-fadeIn { animation: fadeIn 0.2s ease-out; }

/* Dark Mode Styles */
body.dark-mode { background: #1a202c; color: #e2e8f0; }
body.dark-mode .bg-gray-50 { background: #1a202c; }
body.dark-mode .bg-white { background: #2d3748; }
body.dark-mode .text-gray-900 { color: #e2e8f0; }
body.dark-mode .text-gray-700 { color: #cbd5e0; }
body.dark-mode .text-gray-600 { color: #a0aec0; }
body.dark-mode .text-gray-500 { color: #718096; }
body.dark-mode .border-gray-200 { border-color: #4a5568; }
body.dark-mode .material-card { box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.24); }
body.dark-mode .material-card:hover { box-shadow: 0 14px 28px rgba(0,0,0,0.4), 0 10px 10px rgba(0,0,0,0.3); }
body.dark-mode .bg-gray-100 { background: #4a5568; }
```

### Step 3: Add Export Functions (after exportToPDF function)

#### For production.html (production_data.json structure):
```javascript
function exportToExcel(data) {
    if (!data) return;
    // Monthly production analysis
    const monthlyData = data.monthly_analysis.months.map((month, i) => ({
        Mese: month,
        'Difetti': data.monthly_analysis.defect_count[i],
        'Rifacimenti': data.monthly_analysis.rework_count[i],
        'Scarti': data.monthly_analysis.scrap_count[i]
    }));

    const ws = XLSX.utils.json_to_sheet(monthlyData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Analisi Mensile");
    XLSX.writeFile(wb, `Production_${new Date().toISOString().split('T')[0]}.xlsx`);
}

function exportToCSV(data) {
    if (!data) return;
    const monthlyData = data.monthly_analysis.months.map((month, i) => ({
        Mese: month,
        'Difetti': data.monthly_analysis.defect_count[i],
        'Rifacimenti': data.monthly_analysis.rework_count[i],
        'Scarti': data.monthly_analysis.scrap_count[i]
    }));

    const ws = XLSX.utils.json_to_sheet(monthlyData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Production_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}
```

#### For cashflow.html (cashflow_data.json structure):
```javascript
function exportToExcel(data) {
    if (!data) return;
    // Cash flow data
    const cashData = data.cash.months.map((month, i) => ({
        Mese: month,
        'Saldo Cassa': data.cash.monthly_trend[i],
        'Entrate': data.cash.in || 0,
        'Uscite': data.cash.out || 0
    }));

    const ws = XLSX.utils.json_to_sheet(cashData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Cash Flow");
    XLSX.writeFile(wb, `CashFlow_${new Date().toISOString().split('T')[0]}.xlsx`);
}

function exportToCSV(data) {
    if (!data) return;
    const cashData = data.cash.months.map((month, i) => ({
        Mese: month,
        'Saldo Cassa': data.cash.monthly_trend[i]
    }));

    const ws = XLSX.utils.json_to_sheet(cashData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CashFlow_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}
```

#### For salesforce.html (sales_data.json structure):
```javascript
function exportToExcel(data) {
    if (!data) return;
    // Deals by sales rep
    const dealsData = data.deals_closed_month.map(rep => ({
        Nome: rep.name,
        'Deals Chiusi': rep.deals,
        'Valore ($K)': rep.value
    }));

    // Recent deals
    const recentDeals = data.recent_deals.map(deal => ({
        Cliente: deal.client,
        'Valore ($K)': deal.value
    }));

    const wb = XLSX.utils.book_new();
    const ws1 = XLSX.utils.json_to_sheet(dealsData);
    const ws2 = XLSX.utils.json_to_sheet(recentDeals);
    XLSX.utils.book_append_sheet(wb, ws1, "Performance Sales");
    XLSX.utils.book_append_sheet(wb, ws2, "Recent Deals");
    XLSX.writeFile(wb, `Sales_${new Date().toISOString().split('T')[0]}.xlsx`);
}

function exportToCSV(data) {
    if (!data) return;
    const dealsData = data.deals_closed_month.map(rep => ({
        Nome: rep.name,
        'Deals Chiusi': rep.deals,
        'Valore ($K)': rep.value
    }));

    const ws = XLSX.utils.json_to_sheet(dealsData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Sales_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}
```

#### For scad.html (scad.json structure - AR Aging):
```javascript
function exportToExcel(data) {
    if (!data) return;
    // Aging buckets data
    const agingData = data.aging_bucket.map(bucket => ({
        Bucket: bucket.bucket,
        'N. Scadenze': bucket.n_scadenze,
        Valore: bucket.valore,
        '% Perdita': bucket.perc_perdita,
        'Valore Netto': bucket.valore_netto,
        '% sul Totale': bucket.percentuale_su_totale
    }));

    // Top clients risk concentration
    const clientsData = data.concentrazione_rischio.primi_soggetti.map(c => ({
        Cliente: c.ragione_sociale,
        'Valore (€)': c.valore,
        '% sul Totale': c.percentuale_su_totale
    }));

    const wb = XLSX.utils.book_new();
    const ws1 = XLSX.utils.json_to_sheet(agingData);
    const ws2 = XLSX.utils.json_to_sheet(clientsData);
    XLSX.utils.book_append_sheet(wb, ws1, "Aging Buckets");
    XLSX.utils.book_append_sheet(wb, ws2, "Top Clienti");
    XLSX.writeFile(wb, `AR_Scadenzario_${new Date().toISOString().split('T')[0]}.xlsx`);
}

function exportToCSV(data) {
    if (!data) return;
    const agingData = data.aging_bucket.map(bucket => ({
        Bucket: bucket.bucket,
        'N. Scadenze': bucket.n_scadenze,
        Valore: bucket.valore,
        '% Perdita': bucket.perc_perdita,
        'Valore Netto': bucket.valore_netto
    }));

    const ws = XLSX.utils.json_to_sheet(agingData);
    const csv = XLSX.utils.sheet_to_csv(ws);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AR_Scadenzario_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}
```

### Step 4: Add Dark Mode Toggle and ExportDropdown Component
Add these functions before the first component definition:
```javascript
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}

function ExportDropdown({ data }) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="relative" ref={dropdownRef}>
            <button onClick={() => setIsOpen(!isOpen)} className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-all ripple">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2z"/>
                </svg>
                <span className="font-medium">Esporta</span>
                <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="currentColor" viewBox="0 0 20 20">
                    <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"/>
                </svg>
            </button>
            {isOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl z-50 animate-fadeIn">
                    <button onClick={() => { exportToPDF(); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 rounded-t-lg flex items-center gap-3 transition">
                        <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                        </svg>
                        <span className="font-medium">PDF</span>
                    </button>
                    <button onClick={() => { exportToExcel(data); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 flex items-center gap-3 transition">
                        <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                        </svg>
                        <span className="font-medium">Excel (.xlsx)</span>
                    </button>
                    <button onClick={() => { exportToCSV(data); setIsOpen(false); }} className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-700 rounded-b-lg flex items-center gap-3 transition">
                        <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/>
                        </svg>
                        <span className="font-medium">CSV</span>
                    </button>
                </div>
            )}
        </div>
    );
}
```

### Step 5: Update Header Section
Replace the existing export button in the header with:
```jsx
<div className="flex items-center gap-2">
    <button onClick={toggleDarkMode} className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-all ripple" title="Toggle Dark Mode">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <span className="font-medium">Dark</span>
    </button>
    <ExportDropdown data={data} />
</div>
```

## Summary
All files follow the exact same pattern:
1. Add SheetJS library
2. Add Dark Mode CSS
3. Add dashboard-specific export functions (Excel + CSV)
4. Add Dark Mode toggle and ExportDropdown component
5. Update header to use new components

The key difference between dashboards is the export function mapping, which must match each dashboard's JSON data structure.
