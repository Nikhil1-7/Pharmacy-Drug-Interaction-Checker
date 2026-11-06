let currentStatus = "";
let currentTotal = 0;
let currentMedicineIds = [];


// ----------------------------------
// Run when webpage loads
// ----------------------------------

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const checkboxes =
            document.querySelectorAll(
                ".medicine-checkbox"
            );

        checkboxes.forEach(
            function (checkbox) {

                checkbox.addEventListener(
                    "change",
                    updateCount
                );

            }
        );
    }
);


// ----------------------------------
// Update selected medicine count
// ----------------------------------

function updateCount() {

    const selected =
        document.querySelectorAll(
            ".medicine-checkbox:checked"
        );

    document.getElementById(
        "medicineCount"
    ).innerText =
        selected.length + " selected";
}


// ----------------------------------
// Check drug interactions
// ----------------------------------

async function checkInteractions() {

    const selected =
        document.querySelectorAll(
            ".medicine-checkbox:checked"
        );


    // No medicine selected
    if (selected.length === 0) {

        alert(
            "Please select at least one medicine."
        );

        return;
    }


    // Get medicine IDs
  const medicineIds =
    Array.from(selected).map(
        checkbox =>
            parseInt(checkbox.value)
    );

currentMedicineIds = medicineIds;


    try {

        const response =
            await fetch(
                "/check-interactions",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        medicine_ids:
                            medicineIds
                    })
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            alert(data.message);

            return;
        }


        // Store current status
        currentStatus =
            data.status;


        // Calculate total price
        currentTotal =
            data.medicines.reduce(
                function (total, medicine) {

                    return total +
                        medicine.price;

                },
                0
            );


        document.getElementById(
            "totalAmount"
        ).innerText =
            "₹" +
            currentTotal.toFixed(2);


        // Display result
        displayResult(data);

    }
    catch (error) {

        console.error(error);

        alert(
            "Server connection error."
        );
    }
}


// ----------------------------------
// Display interaction result
// ----------------------------------

function displayResult(data) {

    const resultCard =
        document.getElementById(
            "resultCard"
        );


    const resultContent =
        document.getElementById(
            "resultContent"
        );


    resultCard.style.display =
        "block";


    let html = "";


    // ----------------------------------
    // APPROVED
    // ----------------------------------

    if (data.status === "APPROVED") {

        html = `
            <div class="approved">

                <h2>
                    ✓ SALE APPROVED
                </h2>

                <p>
                    No interaction was found
                    in the interaction database.
                </p>

            </div>
        `;
    }


    // ----------------------------------
    // REVIEW
    // ----------------------------------

    else if (data.status === "REVIEW") {

        html = `
            <div class="review">

                <h2>
                    ⚠ PHARMACIST REVIEW REQUIRED
                </h2>

                <p>
                    An interaction was detected.
                </p>
        `;


        data.interactions.forEach(
            function (item) {

                html += `
                    <div class="warning">

                        <strong>
                            ${item.salt1}
                            ↔
                            ${item.salt2}
                        </strong>

                        <p>
                            Severity:
                            ${item.severity}
                        </p>

                        <p>
                            ${item.warning}
                        </p>

                    </div>
                `;
            }
        );


        html += `
            </div>
        `;
    }


    // ----------------------------------
    // BLOCKED
    // ----------------------------------

    else {

        html = `
            <div class="blocked">

                <h2>
                    ✕ SALE BLOCKED
                </h2>

                <p>
                    Severe drug interaction detected.
                </p>

                <p>
                    Pharmacist review is required
                    before the sale can proceed.
                </p>
        `;


        data.interactions.forEach(
            function (item) {

                html += `
                    <div class="warning">

                        <strong>
                            PHARMACIST WARNING
                        </strong>

                        <p>
                            ${item.salt1}
                            ↔
                            ${item.salt2}
                        </p>

                        <p>

                            Severity:

                            <strong>
                                ${item.severity}
                            </strong>

                        </p>

                        <p>
                            ${item.warning}
                        </p>

                    </div>
                `;
            }
        );


        html += `
            </div>
        `;
    }


    // Put HTML inside result section
    resultContent.innerHTML =
        html;


    // Show billing section
    document.getElementById(
        "billingSection"
    ).style.display =
        "block";


    // Get bill button
    const billButton =
        document.getElementById(
            "generateBillButton"
        );


    // ----------------------------------
    // Disable bill if BLOCKED
    // ----------------------------------

    if (data.status === "BLOCKED") {

        billButton.disabled =
            true;

        billButton.innerText =
            "SALE BLOCKED";

        billButton.style.background =
            "#d92d20";
    }


    // ----------------------------------
    // Enable bill
    // ----------------------------------

    else {

        billButton.disabled =
            false;

        billButton.innerText =
            "GENERATE BILL";

        billButton.style.background =
            "#16a05d";
    }
}


// ----------------------------------
// Generate bill
// ----------------------------------

async function generateBill() {

    // Don't allow blocked sale
    if (currentStatus === "BLOCKED") {

        alert(
            "Sale is blocked."
        );

        return;
    }


    // Get patient name
    const patientName =
        document.getElementById(
            "patientName"
        ).value.trim();


    // Get prescription number
    const prescriptionNumber =
        document.getElementById(
            "prescriptionNumber"
        ).value.trim();


    // Check patient name
    if (!patientName) {

        alert(
            "Enter patient name."
        );

        return;
    }


    // Check prescription number
    if (!prescriptionNumber) {

        alert(
            "Enter prescription number."
        );

        return;
    }


    try {

        const response =
            await fetch(
                "/generate-bill",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        patient_name:
                            patientName,

                        prescription_number:
                            prescriptionNumber,

                        total_amount:
                            currentTotal,

                        status:
                            currentStatus,

                        medicine_ids:
                            currentMedicineIds

                    })
                }
            );


        const data =
            await response.json();


        if (!data.success) {

            alert(data.message);

            return;
        }


        alert(
            "Bill generated successfully!\n\n" +
            "Bill Number: " +
            data.bill_id
        );


        // Open bill page
        window.location.href =
            "/bill/" + data.bill_id;

    }
    catch (error) {

        console.error(error);

        alert(
            "Unable to generate bill."
        );
    }
}