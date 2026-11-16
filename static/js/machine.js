const creditValue = document.getElementById("credit-value");
const balanceValue = document.getElementById("balance-value");
const changeValue = document.getElementById("change-value");
const changeDenominations = document.getElementById("change-denominations");
const selectionCode = document.getElementById("selection-code");
const selectedProductText = document.getElementById("selected-product");
const quantityInput = document.getElementById("quantity-input");
const purchaseButton = document.getElementById("purchase-button");
const machineMessage = document.getElementById("machine-message");
const transactionActions = document.getElementById("transaction-actions");
const nextStudentButton = document.getElementById("next-student-button");
const csrfToken = document.querySelector(
    "#csrf-form [name=csrfmiddlewaretoken]"
).value;

let transactionId = null;
let creditCents = 0;
let codeBuffer = "";
let selectedProduct = null;
let processing = false;
let finished = false;

function formatMoney(cents) {
    return "Rs " + (cents / 100).toFixed(2);
}

function showMessage(message, isError) {
    machineMessage.textContent = message;
    machineMessage.classList.toggle("message-error", Boolean(isError));
}

function updateCredit() {
    creditValue.textContent = formatMoney(creditCents);
    balanceValue.textContent = formatMoney(creditCents);
}

function setProcessing(value) {
    processing = value;
    document.querySelectorAll(".denomination-button, .key-button").forEach((button) => {
        button.disabled = value || finished;
    });
    purchaseButton.disabled = value || finished || !selectedProduct;
}

async function sendRequest(url, method, data) {
    const options = {
        method: method,
        headers: { "X-CSRFToken": csrfToken }
    };
    if (data) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.error || "The machine could not complete that action.");
    }
    return result;
}

function clearSelection() {
    codeBuffer = "";
    selectedProduct = null;
    selectionCode.textContent = "--";
    selectedProductText.textContent = "Enter product code";
    purchaseButton.disabled = true;
}

function displayProduct(product) {
    selectedProduct = product;
    selectionCode.textContent = product.product_id;
    if (product.quantity === 0) {
        selectedProductText.textContent = product.name + " — SOLD OUT";
        purchaseButton.disabled = true;
        showMessage("SOLD OUT — " + product.name + " is not available.", true);
        return;
    }

    selectedProductText.textContent =
        product.name + " · " + formatMoney(product.price_cents) + " · " + product.quantity + " left";
    purchaseButton.disabled = processing || finished;
    showMessage("Product selected. Enter a quantity, then dispense.", false);
}

async function refreshProductDisplay() {
    if (processing || finished) {
        return;
    }

    try {
        const response = await fetch("/api/products", { cache: "no-store" });
        if (!response.ok) {
            throw new Error("The stock list could not be refreshed.");
        }

        const latestProducts = await response.json();
        if (
            latestProducts.length !== products.length ||
            latestProducts.some(
                (latest) => !products.some(
                    (product) =>
                        product.product_id === latest.product_id &&
                        product.category === latest.category
                )
            )
        ) {
            if (transactionId === null) {
                window.location.reload();
            } else {
                showMessage(
                    "The product list changed. Finish this transaction; the updated list will appear for the next student.",
                    false
                );
            }
            return;
        }

        latestProducts.forEach((latest) => {
            const product = products.find(
                (item) => item.product_id === latest.product_id
            );
            Object.assign(product, latest);

            const productSlot = document.querySelector(
                '[data-product="' + product.product_id + '"]'
            );
            const stockLabel = document.querySelector(
                '[data-stock-for="' + product.product_id + '"]'
            );
            productSlot.querySelector(".product-name").textContent = product.name;
            productSlot.querySelector(".product-price").textContent =
                formatMoney(product.price_cents);
            productSlot.querySelector(".product-thumb").src =
                "/static/" + product.image;
            stockLabel.textContent = product.quantity === 0
                ? "SOLD OUT"
                : product.quantity + " LEFT";
            productSlot.classList.toggle("sold-out", product.quantity === 0);
        });

        if (selectedProduct) {
            selectedProduct = products.find(
                (item) => item.product_id === selectedProduct.product_id
            );
            selectedProductText.textContent = selectedProduct.quantity === 0
                ? selectedProduct.name + " — SOLD OUT"
                : selectedProduct.name + " · " +
                    formatMoney(selectedProduct.price_cents) + " · " +
                    selectedProduct.quantity + " left";
            purchaseButton.disabled =
                processing || finished || selectedProduct.quantity === 0;
        }
    } catch (error) {
        if (!processing && !finished) {
            showMessage(error.message, true);
        }
    }
}

function startTransaction() {
    transactionId = null;
    creditCents = 0;
    finished = false;
    clearSelection();
    updateCredit();
    changeValue.textContent = formatMoney(0);
    changeDenominations.textContent = "Change denominations appear here.";
    transactionActions.hidden = true;
    nextStudentButton.hidden = true;
    showMessage("Welcome. Insert money to begin.", false);
    setProcessing(false);
}

document.querySelectorAll(".denomination-button").forEach((button) => {
    button.addEventListener("click", async () => {
        if (processing || finished) {
            return;
        }

        setProcessing(true);
        try {
            if (transactionId === null) {
                const transaction = await sendRequest("/api/transactions", "POST");
                transactionId = transaction.transaction_id;
            }
            const result = await sendRequest(
                "/api/transactions/" + transactionId + "/insert",
                "POST",
                { denomination_cents: Number(button.dataset.denomination) }
            );
            creditCents = result.credit_cents;
            updateCredit();
            showMessage("Inserted " + button.textContent.trim() + ".", false);
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            setProcessing(false);
        }
    });
});

document.querySelectorAll(".key-button").forEach((button) => {
    button.addEventListener("click", () => {
        if (processing || finished) {
            return;
        }

        const key = button.dataset.key;
        if (key === "clear") {
            clearSelection();
            showMessage("Selection cleared.", false);
            return;
        }

        if (key === "confirm") {
            const product = products.find((item) => item.product_id === codeBuffer);
            if (!product) {
                selectedProduct = null;
                selectionCode.textContent = codeBuffer || "--";
                selectedProductText.textContent = "Product code not found";
                purchaseButton.disabled = true;
                showMessage("Product code not found. Check the code and try again.", true);
                return;
            }
            displayProduct(product);
            return;
        }

        if (codeBuffer.length < 2) {
            codeBuffer += key;
            selectionCode.textContent = codeBuffer;
            selectedProduct = null;
            selectedProductText.textContent = "Press OK to confirm code";
            purchaseButton.disabled = true;
        }
    });
});

purchaseButton.addEventListener("click", async () => {
    if (!selectedProduct || processing || finished || transactionId === null) {
        return;
    }

    const quantity = Number(quantityInput.value);
    if (!Number.isInteger(quantity) || quantity < 1) {
        showMessage("Enter a quantity of at least 1.", true);
        return;
    }

    setProcessing(true);
    try {
        const result = await sendRequest(
            "/api/transactions/" + transactionId + "/purchase",
            "POST",
            { product_id: selectedProduct.product_id, quantity: quantity }
        );
        creditCents = result.remaining_credit_cents;
        selectedProduct.quantity = result.stock_remaining;
        updateCredit();

        const stockLabel = document.querySelector(
            '[data-stock-for="' + result.product_id + '"]'
        );
        const productSlot = document.querySelector(
            '[data-product="' + result.product_id + '"]'
        );
        if (result.stock_remaining === 0) {
            stockLabel.textContent = "SOLD OUT";
            productSlot.classList.add("sold-out");
        } else {
            stockLabel.textContent = result.stock_remaining + " LEFT";
        }

        displayProduct(selectedProduct);
        quantityInput.value = "1";
        transactionActions.hidden = false;
        showMessage(
            "Dispensed " + result.quantity_purchased + " × " + result.product_name +
            ". Remaining balance " + formatMoney(creditCents) + ". Continue or exit.",
            false
        );
    } catch (error) {
        showMessage(error.message, true);
    } finally {
        setProcessing(false);
    }
});

document.getElementById("continue-button").addEventListener("click", () => {
    transactionActions.hidden = true;
    quantityInput.value = "1";
    clearSelection();
    showMessage("Select another product or insert more money.", false);
});

document.getElementById("exit-button").addEventListener("click", async () => {
    if (processing || finished || transactionId === null) {
        return;
    }

    setProcessing(true);
    try {
        const result = await sendRequest(
            "/api/transactions/" + transactionId + "/finish",
            "POST"
        );
        finished = true;
        creditCents = 0;
        updateCredit();
        changeValue.textContent = formatMoney(result.change_returned_cents);
        changeDenominations.textContent = result.change_denominations.length
            ? result.change_denominations.map((value) => formatMoney(value)).join("  +  ")
            : "No change returned.";
        transactionActions.hidden = true;
        nextStudentButton.hidden = false;
        setProcessing(false);
        showMessage(
            "Transaction complete. Change returned: " +
            formatMoney(result.change_returned_cents) + ".",
            false
        );
    } catch (error) {
        setProcessing(false);
        showMessage(error.message, true);
    }
});

nextStudentButton.addEventListener("click", () => {
    window.location.reload();
});

startTransaction();
window.setInterval(refreshProductDisplay, 5000);
