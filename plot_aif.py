# -*- coding: utf-8 -*-
"""Web interface for plotting multiple AIF files."""
# pylint: disable-msg=invalid-name

import os
import tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template_string, request, send_file, after_this_request
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Global counter for color assignment
color_counter = 0

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIF Isotherm Plotter</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            margin-bottom: 20px;
            text-align: center;
            font-size: 14px;
        }
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .upload-area.dragover {
            border-color: #667eea;
            background: #f0f3ff;
        }
        .file-input {
            display: none;
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 10px;
        }
        .legend-panel {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .legend-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }
        .legend-item {
            display: flex;
            align-items: center;
            padding: 8px;
            margin: 5px 0;
            background: white;
            border-radius: 6px;
            gap: 10px;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .legend-name {
            flex-grow: 1;
            font-size: 14px;
        }
        .legend-delete {
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            cursor: pointer;
            font-size: 12px;
        }
        .legend-delete:hover {
            background: #c82333;
        }
        .btn {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            margin: 5px;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-group {
            text-align: center;
            margin: 20px 0;
        }
        .plot-container {
            text-align: center;
            margin-top: 20px;
        }
        .plot-container img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .options {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .option-group {
            flex: 1;
            min-width: 200px;
        }
        .option-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #555;
        }
        .option-group select, .option-group input {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        .info-box {
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #004085;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AIF Isotherm Plotter</h1>
        <p class="subtitle">Plot multiple adsorption isotherm files</p>

        <div class="info-box">
            Drag & drop multiple .aif files or click to select. Each file will be added to the plot.
        </div>

        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📊</div>
            <div>Click to select or drag & drop multiple .aif files</div>
            <input type="file" name="file" id="fileInput" class="file-input" accept=".aif" multiple>
        </div>

        <div class="legend-panel" id="legendPanel" style="display: none;">
            <div class="legend-title">Loaded Files:</div>
            <div id="legendItems"></div>
        </div>

        <div class="options">
            <div class="option-group">
                <label for="pressureType">Pressure Type</label>
                <select id="pressureType">
                    <option value="relative">Relative Pressure (p/p₀)</option>
                    <option value="absolute">Absolute Pressure</option>
                </select>
            </div>
            <div class="option-group">
                <label for="yAxis">Y-Axis</label>
                <select id="yAxis">
                    <option value="amount">Amount Adsorbed</option>
                </select>
            </div>
        </div>

        <div class="btn-group">
            <button class="btn" id="plotBtn">Update Plot</button>
            <button class="btn btn-secondary" id="clearBtn">Clear All</button>
        </div>

        <div class="plot-container" id="plotContainer"></div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const legendPanel = document.getElementById('legendPanel');
        const legendItems = document.getElementById('legendItems');
        const plotBtn = document.getElementById('plotBtn');
        const clearBtn = document.getElementById('clearBtn');
        const plotContainer = document.getElementById('plotContainer');
        const pressureType = document.getElementById('pressureType');
        const yAxis = document.getElementById('yAxis');

        let loadedFiles = [];

        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        function handleFiles(files) {
            for (let file of files) {
                if (file.name.endsWith('.aif')) {
                    uploadFile(file);
                }
            }
        }

        function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/parse_aif', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadedFiles.push({
                        id: data.file_id,
                        name: data.name,
                        color: data.color,
                        data: data.data
                    });
                    updateLegend();
                    updatePlot();
                }
            })
            .catch(err => console.error(err));
        }

        function updateLegend() {
            if (loadedFiles.length > 0) {
                legendPanel.style.display = 'block';
            } else {
                legendPanel.style.display = 'none';
            }

            legendItems.innerHTML = loadedFiles.map((f, i) => `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${f.color};"></div>
                    <div class="legend-name">${f.name}</div>
                    <button class="legend-delete" onclick="removeFile(${i})">Remove</button>
                </div>
            `).join('');
        }

        function removeFile(index) {
            loadedFiles.splice(index, 1);
            updateLegend();
            updatePlot();
        }

        clearBtn.addEventListener('click', () => {
            loadedFiles = [];
            updateLegend();
            plotContainer.innerHTML = '';
        });

        plotBtn.addEventListener('click', updatePlot);

        function updatePlot() {
            if (loadedFiles.length === 0) {
                plotContainer.innerHTML = '';
                return;
            }

            const plotData = loadedFiles.map(f => ({
                id: f.id,
                name: f.name,
                color: f.color,
                x_axis: pressureType.value === 'relative' ? 'p_over_p0' : 'pressure',
                data: f.data
            }));

            fetch('/generate_plot', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    files: plotData,
                    plot_type: pressureType.value
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    plotContainer.innerHTML = `<img src="/plot/${data.image}" alt="Isotherm Plot">`;
                }
            })
            .catch(err => console.error(err));
        }

        // Auto-refresh plot when options change
        pressureType.addEventListener('change', updatePlot);
    </script>
</body>
</html>
'''


# Color palette for different datasets
COLORS = [
    '#2E86AB', '#E94F37', '#3BB273', '#F6BD60', '#A84A32',
    '#6B4C9A', '#40BCD8', '#F7A072', '#9BC53D', '#E55934',
    '#FA7921', '#5BC0EB', '#9DE0AD', '#E85D75', '#FC5130'
]


@app.route('/')
def index():
    """Render the main page."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/parse_aif', methods=['POST'])
def parse_aif():
    """Parse AIF file and return data."""
    try:
        file = request.files.get('file')
        if not file:
            return {'success': False, 'error': 'No file uploaded'}

        if not file.filename.lower().endswith('.aif'):
            return {'success': False, 'error': 'Only .aif files are supported'}

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.aif', delete=False) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        try:
            # Parse AIF file
            data = parse_aif_file(tmp_path)

            global color_counter
            color_index = color_counter % len(COLORS)
            color_counter += 1

            return {
                'success': True,
                'file_id': str(uuid.uuid4()),
                'name': os.path.splitext(file.filename)[0],
                'color': COLORS[color_index],
                'data': data
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return {'success': False, 'error': str(e)}


def parse_aif_file(filepath):
    """Parse AIF file and extract adsorption/desorption data."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Extract metadata
    metadata = {}
    ads_data = []
    des_data = []
    in_ads = False
    in_des = False

    for line in lines:
        line = line.strip()

        # Parse metadata
        if line.startswith('_exptl_') or line.startswith('_adsnt_') or line.startswith('_units_'):
            if ' ' in line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    # Keep original prefix to avoid key collisions
                    raw_key = parts[0]
                    value = parts[1].strip("'")

                    if raw_key.startswith('_exptl_'):
                        key = raw_key.replace('_exptl_', 'exptl_')
                    elif raw_key.startswith('_adsnt_'):
                        key = raw_key.replace('_adsnt_', 'adsnt_')
                    elif raw_key.startswith('_units_'):
                        key = raw_key.replace('_units_', 'units_')
                    else:
                        key = raw_key

                    metadata[key] = value

        # Check for adsorption data section
        if '_adsorp_' in line:
            in_ads = True
            in_des = False
            continue

        # Check for desorption data section
        if '_desorp_' in line:
            in_ads = False
            in_des = True
            continue

        # Skip loop declarations and column headers
        if line.startswith('loop_') or line.startswith('_') or not line:
            continue

        # Parse data line
        try:
            values = line.split()
            if len(values) >= 3:
                pressure = float(values[0])
                p0 = float(values[1])
                amount = float(values[2])

                if in_ads:
                    ads_data.append({
                        'pressure': pressure,
                        'p0': p0,
                        'p_over_p0': pressure / p0 if p0 > 0 else 0,
                        'amount': amount
                    })
                elif in_des:
                    des_data.append({
                        'pressure': pressure,
                        'p0': p0,
                        'p_over_p0': pressure / p0 if p0 > 0 else 0,
                        'amount': amount
                    })
        except (ValueError, IndexError):
            continue

    return {
        'ads': ads_data,
        'des': des_data,
        'metadata': metadata
    }


@app.route('/generate_plot', methods=['POST'])
def generate_plot():
    """Generate plot from multiple AIF files."""
    try:
        data = request.json
        files = data.get('files', [])
        plot_type = data.get('plot_type', 'relative')

        if not files:
            return {'success': False, 'error': 'No files provided'}

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot each file
        for file_info in files:
            file_data = file_info['data']
            color = file_info['color']
            name = file_info['name']

            # Get metadata for legend
            metadata = file_data.get('metadata', {})
            sample_id = metadata.get('adsnt_sample_id', name)
            material_id = metadata.get('adsnt_material_id', '')
            adsorptive = metadata.get('exptl_adsorptive', 'unknown gas')
            # Clean up adsorptive (remove "1: " prefix if present)
            if adsorptive.startswith('1: '):
                adsorptive = adsorptive[3:]
            # Get temperature with unit from exptl_temperature and units_temperature
            temp_value = metadata.get('exptl_temperature', '')
            temp_unit = metadata.get('units_temperature', 'K')
            temperature = f'{temp_value}' if temp_value else ''

            # Format legend label: sample, material_id (if exists), gas, temp, Ads/Des
            if material_id and material_id != sample_id:
                legend_label = f'{sample_id}, {material_id}, {adsorptive}, {temperature}K'
            else:
                legend_label = f'{sample_id}, {adsorptive}, {temperature}K'

            ads = file_data.get('ads', [])
            des = file_data.get('des', [])

            # Determine x-axis data
            if file_info.get('x_axis') == 'pressure':
                x_key = 'pressure'
            else:
                x_key = 'p_over_p0'

            # Plot adsorption (solid line with markers)
            if ads:
                ads_x = [d[x_key] for d in ads]
                ads_y = [d['amount'] for d in ads]
                ax.scatter(ads_x, ads_y, c=color, s=100, marker='o', label=f'{legend_label}, Ads',
                          zorder=3, edgecolors='none')
                ax.plot(ads_x, ads_y, c=color, linewidth=2.5, zorder=2)

            # Plot desorption (hollow circles only, no line)
            if des:
                des_x = [d[x_key] for d in des]
                des_y = [d['amount'] for d in des]
                ax.scatter(des_x, des_y, color=color, s=80, marker='o', label=f'{legend_label}, Des',
                          zorder=3, facecolors='none', edgecolors=color, linewidths=1.5)

        # Labels and title
        if plot_type == 'relative':
            ax.set_xlabel('Relative Pressure (p/p₀)', fontsize=14)
        else:
            pressure_unit = files[0]['data'].get('metadata', {}).get('pressure', 'Torr')
            ax.set_xlabel(f'Pressure ({pressure_unit})', fontsize=14)

        loading_unit = files[0]['data'].get('metadata', {}).get('loading', 'cm³ STP/g')
        ax.set_ylabel(f'Amount Adsorbed ({loading_unit})', fontsize=14)
        ax.set_title('Adsorption Isotherms', fontsize=16, fontweight='bold', pad=15)

        # Grid
        ax.grid(True, linestyle='--', alpha=0.7, zorder=1)
        ax.set_axisbelow(True)

        # Set y-axis minimum to 0
        ax.set_ylim(bottom=0)

        # Legend
        ax.legend(loc='best', fontsize=10, ncol=2)

        # Tick label size
        ax.tick_params(axis='both', labelsize=11)

        # Tight layout
        plt.tight_layout()

        # Save figure
        output_filename = f"plot_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        return {
            'success': True,
            'image': output_filename
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/plot/<filename>')
def get_plot(filename):
    """Serve the generated plot image."""
    filepath = os.path.join(tempfile.gettempdir(), filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        return response

    return send_file(filepath, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
