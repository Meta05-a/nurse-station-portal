let selectedPatientId = null;
let currentPatientData = null;

document.addEventListener("DOMContentLoaded", () => {
    loadPatients("all");
});

async function loadPatients(floor) {
    try {
        const response = await fetch(`/api/patients?floor=${floor}`);
        const patients = await response.json();
        
        const tbody = document.getElementById("patientTableBody");
        tbody.innerHTML = "";

        if (patients.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;">No patients registered on this floor unit.</td></tr>`;
            return;
        }

        patients.forEach(patient => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${patient.room}</strong></td>
                <td>${patient.name}</td>
                <td>Floor ${patient.floor}</td>
                <td>${patient.condition}</td>
                <td>${patient.doctor}</td>
                <td>Leaves in ${patient.days_remaining} days</td>
                <td>
                    <button class="btn btn-secondary" onclick="selectPatient(${patient.id})">View</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("Error fetching patient catalog:", error);
    }
}

function filterFloor() {
    const floor = document.getElementById("floorSelect").value;
    loadPatients(floor);
}

async function selectPatient(id) {
    try {
        const response = await fetch(`/api/patients/${id}`);
        const patient = await response.json();

        selectedPatientId = patient.id;
        currentPatientData = patient;

        document.getElementById("patientName").innerText = patient.name;
        document.getElementById("patientDoctor").innerText = `Assigned: ${patient.doctor}`;
        document.getElementById("patientCode").innerText = patient.patient_code;
        document.getElementById("patientRoom").innerText = patient.room;
        document.getElementById("patientFloor").innerText = `Floor ${patient.floor}`;
        document.getElementById("patientAge").innerText = patient.age;
        document.getElementById("patientAdmitted").innerText = patient.admitted_date;
        document.getElementById("patientCondition").innerText = patient.condition;
        document.getElementById("patientDischargeDate").innerText = patient.discharge_date;
        document.getElementById("dischargeStatus").innerText = `Leaves in ${patient.days_remaining} days`;
        document.getElementById("patientNotes").innerText = patient.notes || "No extra notes logged.";

        document.getElementById("emptyState").classList.add("hidden");
        document.getElementById("detailContent").classList.remove("hidden");
    } catch (error) {
        console.error("Error retrieving patient file:", error);
    }
}

function openAddModal() {
    document.getElementById("modalTitle").innerText = "Register New Patient";
    document.getElementById("formPatientId").value = "";
    document.getElementById("patientForm").reset();
    document.getElementById("patientModal").classList.remove("hidden");
}

function openEditModal() {
    if (!currentPatientData) return;
    
    document.getElementById("modalTitle").innerText = "Edit Patient Details";
    document.getElementById("formPatientId").value = currentPatientData.id;
    document.getElementById("formName").value = currentPatientData.name;
    document.getElementById("formAge").value = currentPatientData.age;
    document.getElementById("formFloor").value = currentPatientData.floor;
    document.getElementById("formRoom").value = currentPatientData.room;
    document.getElementById("formCondition").value = currentPatientData.condition;
    document.getElementById("formDoctor").value = currentPatientData.doctor;
    document.getElementById("formStayDays").value = currentPatientData.days_remaining;
    document.getElementById("formNotes").value = currentPatientData.notes;

    document.getElementById("patientModal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("patientModal").classList.add("hidden");
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    const id = document.getElementById("formPatientId").value;
    const payload = {
        name: document.getElementById("formName").value,
        age: document.getElementById("formAge").value,
        floor: document.getElementById("formFloor").value,
        room: document.getElementById("formRoom").value,
        condition: document.getElementById("formCondition").value,
        doctor: document.getElementById("formDoctor").value,
        stay_days: document.getElementById("formStayDays").value,
        notes: document.getElementById("formNotes").value
    };

    const isEdit = id !== "";
    const url = isEdit ? `/api/patients/${id}` : "/api/patients";
    const method = isEdit ? "PUT" : "POST";

    try {
        const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            closeModal();
            const currentFloor = document.getElementById("floorSelect").value;
            loadPatients(currentFloor);
            if (isEdit) selectPatient(id);
        } else {
            alert("Failed to save patient record. Please verify fields.");
        }
    } catch (error) {
        console.error("Error submitting patient form:", error);
    }
}

async function dischargePatient() {
    if (!selectedPatientId) return;
    if (!confirm("Are you sure you want to discharge this patient and remove them from active tracking?")) return;

    try {
        const response = await fetch(`/api/patients/${selectedPatientId}`, { method: "DELETE" });
        if (response.ok) {
            document.getElementById("detailContent").classList.add("hidden");
            document.getElementById("emptyState").classList.remove("hidden");
            selectedPatientId = null;
            currentPatientData = null;
            filterFloor();
        }
    } catch (error) {
        console.error("Error discharging patient:", error);
    }
}

function downloadRecord() {
    if (!selectedPatientId) return;
    window.location.href = `/api/patients/${selectedPatientId}/export`;
}
