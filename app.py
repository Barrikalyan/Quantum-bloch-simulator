# Ensure matplotlib uses a non-interactive backend before any code that may start a GUI.
import matplotlib
matplotlib.use('Agg')  # Use a headless backend to avoid Tkinter/main-thread GUI issues
from flask import Flask, render_template, request, url_for, redirect
from qiskit import QuantumCircuit
from qiskit.quantum_info import partial_trace, DensityMatrix, Pauli
from qiskit.visualization import plot_bloch_vector
import matplotlib.pyplot as plt
import numpy as np
import os
import uuid
import re
# Ensure matplotlib uses a non-interactive backend before any code that may start a GUI.
import matplotlib
matplotlib.use('Agg')  # Use a headless backend to avoid Tkinter/main-thread GUI issues

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'static', 'main', 'templates'), static_folder=os.path.join(os.path.dirname(__file__), 'static', 'main', 'static'), root_path=os.path.dirname(__file__))
SECTIONS = {
    "Impacts": [
        "Enhance intuition about quantum superposition and entanglement",
        "Accelerate the development of quantum algorithms",
        "Facilitate debugging of quantum circuits",
        "Support interdisciplinary collaboration between physicists, computer scientists, and engineers",
        "Contribute to the broader adoption of quantum technologies in industry and academia"
    ],
    "Benefits": [
        "Interactive Visualization: Real-time rendering of Bloch spheres for individual qubits, showing how quantum states evolve through circuit operations",
        "Multi-Qubit Support: Handles complex entangled systems, displaying reduced density matrices for selected subsystems",
        "Educational Value: Serves as an excellent teaching tool for quantum computing courses, making abstract concepts tangible",
        "Research Utility: Enables rapid prototyping and testing of quantum algorithms without requiring physical quantum hardware",
        "Accessibility: Web-based interface works on any device with a modern browser, no specialized software installation needed",
        "Extensibility: Built with open-source libraries, allowing researchers to modify and extend functionality"
    ],
    "Feasibility": [
        "Technical Maturity: Leverages well-established libraries like Qiskit, which powers real quantum research worldwide",
        "Performance: Efficient enough for interactive use with circuits of reasonable size (up to 10-15 qubits on standard hardware)",
        "Scalability: Modular architecture allows for future enhancements, such as cloud-based computation for larger circuits",
        "Maintainability: Clean separation of frontend (HTML/CSS/JS) and backend (Python/Flask) simplifies updates and debugging",
        "Cost-Effectiveness: Runs on commodity hardware, making quantum education accessible without expensive lab equipment"
    ],
}

def parse_info_md(md_path):
    sections = {"Impacts": [], "Benefits": [], "Feasibility": [], "Technologies": []}
    if not os.path.exists(md_path):
        return sections
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = [ln.strip() for ln in f.readlines()]

    for ln in lines:
        if not ln:
            continue
        # Feasibility-related lines (collect text after colon if present)
        if ln.lower().startswith(('feasibility', 'viability', 'scalability', 'practic')):
            parts = ln.split(':', 1)
            sections['Feasibility'].append(parts[1].strip() if len(parts) > 1 else ln)
            continue
        # Benefits / impacts audience & usage
        if any(ln.lower().startswith(prefix) for prefix in (
            'students', 'debugging', 'supports experiments', 'researcher', 'researchers', 'developers', 'educators'
        )):
            parts = ln.split(':', 1)
            text = parts[1].strip() if len(parts) > 1 else ln
            sections['Benefits'].append(text)
            continue
        # Technologies stack lines formatted as "Name – description"
        if '–' in ln or '-' in ln:
            sections['Technologies'].append(ln)

    # If no explicit impacts, mirror benefits into impacts for display
    if not sections['Impacts'] and sections['Benefits']:
        sections['Impacts'] = list(sections['Benefits'])
    return sections

IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'main', 'static', 'images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# --- Decomposition helpers ---
def apply_ch(qc, control, target):
    qc.sdg(target)
    qc.h(target)
    qc.t(target)
    qc.cx(control, target)
    qc.tdg(target)
    qc.h(target)
    qc.cx(control, target)
    qc.t(target)
    qc.h(target)
    qc.s(target)

def apply_cswap(qc, control, target1, target2):
    qc.cx(target2, target1)
    qc.ccx(control, target1, target2)
    qc.cx(target2, target1)

# --- Supported gates ---
GATE_ARGS = {
    "H": 1, "X": 1, "Y": 1, "Z": 1, "S": 1, "SDG": 1, "T": 1, "TDG": 1,
    "CX": 2, "CNOT": 2, "CZ": 2, "CH": 2, "SWAP": 2,
    "CSWAP": 3, "CCX": 3, "TOFFOLI": 3,
    "RX": 2, "RY": 2, "RZ": 2,
    "U3": 4
}

# --- Build circuit from input ---
def build_circuit_from_input(input_text):
    lines = input_text.strip().split('\n')
    qubits = set()
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        for p in parts[1:]:
            try:
                qubits.add(int(p))
            except ValueError:
                pass
    if not qubits:
        raise ValueError("No valid qubits found in the circuit input.")

    num_qubits = max(qubits) + 1
    qc = QuantumCircuit(num_qubits)

    for line_no, line in enumerate(lines, start=1):
        parts = line.split()
        if not parts:
            continue
        gate = parts[0].upper()
        if gate not in GATE_ARGS:
            raise ValueError(f"Line {line_no}: Unsupported gate '{gate}'")
        expected_args = GATE_ARGS[gate]
        if len(parts) - 1 != expected_args:
            raise ValueError(f"Line {line_no}: Gate '{gate}' expects {expected_args} argument(s), got {len(parts)-1}")

        try:
            if gate == 'H':
                qc.h(int(parts[1]))
            elif gate == 'X':
                qc.x(int(parts[1]))
            elif gate == 'Y':
                qc.y(int(parts[1]))
            elif gate == 'Z':
                qc.z(int(parts[1]))
            elif gate in ['CX','CNOT']:
                qc.cx(int(parts[1]), int(parts[2]))
            elif gate in ['CCX','TOFFOLI']:
                qc.ccx(int(parts[1]), int(parts[2]), int(parts[3]))
            elif gate == 'CZ':
                qc.cz(int(parts[1]), int(parts[2]))
            elif gate == 'CH':
                apply_ch(qc, int(parts[1]), int(parts[2]))
            elif gate == 'SWAP':
                qc.swap(int(parts[1]), int(parts[2]))
            elif gate == 'CSWAP':
                apply_cswap(qc, int(parts[1]), int(parts[2]), int(parts[3]))
            elif gate == 'S':
                qc.s(int(parts[1]))
            elif gate == 'SDG':
                qc.sdg(int(parts[1]))
            elif gate == 'T':
                qc.t(int(parts[1]))
            elif gate == 'TDG':
                qc.tdg(int(parts[1]))
            elif gate == 'RX':
                qc.rx(float(parts[1]), int(parts[2]))
            elif gate == 'RY':
                qc.ry(float(parts[1]), int(parts[2]))
            elif gate == 'RZ':
                qc.rz(float(parts[1]), int(parts[2]))
            elif gate == 'U3':
                qc.u(float(parts[1]), float(parts[2]), float(parts[3]), int(parts[4]))
        except Exception as e:
            raise ValueError(f"Line {line_no}: Error applying gate '{gate}' - {str(e)}")

    return qc

# --- Bloch sphere helpers ---
def create_bloch_plot(bloch_vec, title="Qubit"):
    fig = plot_bloch_vector(bloch_vec, title=title)
    ax = fig.gca()
    ax.set_facecolor("#f0f0f0")
    fig.patch.set_facecolor("#f9f9f9")
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.scatter([0], [0], color='red', s=30, label='Origin')  
    return fig

def bloch_to_dirac(bloch_vec):
    x, y, z = bloch_vec
    theta = np.arccos(np.clip(z, -1, 1))
    phi = np.arctan2(y, x)
    alpha = np.cos(theta / 2)
    beta = np.exp(1j * phi) * np.sin(theta / 2)
    return alpha, beta

def classify_qubit(bloch_vec, purity, tol=1e-2):
    if purity < 1 - tol:
        return "Mixed/Superposition"
    x, y, z = bloch_vec
    if np.abs(z - 1) < tol:
        return "|0> (pure)"
    elif np.abs(z + 1) < tol:
        return "|1> (pure)"
    else:
        return "Superposition"

# --- Flask route ---
@app.route('/', methods=['GET','POST'])
def index():
    plots = []
    circuit_input = ''
    selected_qubits = []
    num_qubits = 0
    error_msg = ''
    error_line = None
    error_message = ''
    circuit_diagram = None

    if request.method == 'POST':
        circuit_input = request.form.get('circuit_input','')
        selected_qubits = [int(q) for q in request.form.getlist('qubits')]

        try:
            qc = build_circuit_from_input(circuit_input)
            num_qubits = qc.num_qubits

            # Save circuit diagram
            circuit_filename = f"circuit_{uuid.uuid4().hex[:6]}.png"
            circuit_path = os.path.join(IMAGE_FOLDER, circuit_filename)
            qc.draw(output='mpl').savefig(circuit_path, dpi=150, bbox_inches='tight')
            plt.close('all')
            circuit_diagram = url_for('static', filename=f"images/{circuit_filename}")

            if any(q >= num_qubits for q in selected_qubits):
                error_msg = "Selected qubit index exceeds circuit size."
            else:
                from qiskit.quantum_info import Statevector, DensityMatrix
                sv = Statevector.from_instruction(qc)
                rho = DensityMatrix(sv)
                density_matrix_data = rho.data

                lines = circuit_input.strip().split('\n')

                for qidx in selected_qubits:
                    reduced_rho = partial_trace(rho, [i for i in range(num_qubits) if i != qidx])
                    bloch_vec = np.array([
                        np.real(np.trace(reduced_rho.data @ Pauli('X').to_matrix())),
                        np.real(np.trace(reduced_rho.data @ Pauli('Y').to_matrix())),
                        np.real(np.trace(reduced_rho.data @ Pauli('Z').to_matrix()))
                    ])
                    fig = create_bloch_plot(bloch_vec, title=f"Qubit {qidx}")

                    # Save Bloch plot
                    gates_for_qubit = []
                    for line in lines:
                        if re.search(rf'\b{qidx}\b', line):
                            clean_line = re.sub(r'[^A-Za-z0-9]', '', line)
                            gates_for_qubit.append(clean_line)
                    gates_str = "_".join(gates_for_qubit)
                    random_str = uuid.uuid4().hex[:6]
                    filename = f"{gates_str}_{random_str}.png"
                    filepath = os.path.join(IMAGE_FOLDER, filename)
                    fig.savefig(filepath, dpi=150, bbox_inches='tight')
                    plt.close(fig)

                    # Dirac notation
                    alpha, beta = bloch_to_dirac(bloch_vec)
                    dirac_notation = f"|ψ> = ({alpha:.2f})|0> + ({beta:.2f})|1>"

                    # Probabilities
                    p0 = np.real(np.trace(reduced_rho.data @ np.array([[1,0],[0,0]])))
                    p1 = np.real(np.trace(reduced_rho.data @ np.array([[0,0],[0,1]])))
                    p0 = np.round(p0*100, 2)
                    p1 = np.round(p1*100, 2)

                    # Purity & type
                    red_rho_str = str(np.round(reduced_rho.data,3))
                    purity = np.real(np.trace(reduced_rho.data @ reduced_rho.data))
                    purity = np.round(purity, 3)
                    state_type = classify_qubit(bloch_vec, purity)

                    plots.append({
                        "url": url_for('static', filename=f"images/{filename}"),
                        "bloch": bloch_vec,
                        "dirac": dirac_notation,
                        "rho": red_rho_str,
                        "purity": purity,
                        "state_type": state_type,
                        "p0": p0,
                        "p1": p1
                    })

        except Exception as e:
            error_msg = str(e)

    return render_template('index.html',
                           circuit_input=circuit_input,
                           num_qubits=num_qubits,
                           selected_qubits=selected_qubits,
                           plots=plots,
                           error_msg=error_msg,
                           circuit_diagram=circuit_diagram)

@app.route('/about')
def about():
    md_path = os.path.join(os.path.dirname(__file__), 'static', 'main', 'info.md')
    sections = parse_info_md(md_path)
    # Merge with any hardcoded SECTIONS overrides
    merged = {k: (SECTIONS.get(k) or []) for k in set(list(sections.keys()) + list(SECTIONS.keys()))}
    for k, v in sections.items():
        if v:
            merged[k] = v
    return render_template('about.html', sections=merged)

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/notes')
def notes():
    # Simple static notes page — no dynamic data required for the cards
    return render_template('notes.html')

if __name__ == '__main__':
    app.run(debug=True)