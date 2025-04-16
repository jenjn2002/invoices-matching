const fileInput = document.getElementById("file-input");
const resultsTable = document.getElementById("results-table");
const confirmBtn = document.getElementById("confirm-btn");

let selectedMatches = {};
let searchResults = [];

fileInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // Step 1: Check if the file is a PDF
  if (!file.name.endsWith(".pdf")) {
    alert("❌ Please upload a PDF file.");
    return;
  }

  try {
    // Step 2: Send the PDF to the mock backend for processing
    const formData = new FormData();
    formData.append("file", file);

    const pdfProcessResponse = await fetch("http://209.124.85.88:5001/process-pdf", {
      method: "POST",
      body: formData,
    });

    if (!pdfProcessResponse.ok) {
      throw new Error(`PDF processing failed: ${pdfProcessResponse.status}`);
    }

    const jsonData = await pdfProcessResponse.json();
    console.log("Received JSON from mock backend:", jsonData);

    // Step 3: Send the JSON data to your /search endpoint
    console.log("Sending JSON to /search:", jsonData);
    const searchResponse = await fetch("http://209.124.85.88:5000/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(jsonData),
    });

    if (!searchResponse.ok) {
      const errorData = await searchResponse.json();
      console.error("Search endpoint error:", errorData);
      throw new Error(`Search failed: ${searchResponse.status} - ${errorData.error}`);
    }

    searchResults = await searchResponse.json();
    console.log("Frontend received search results:", searchResults);
    displayResults(searchResults);
  } catch (error) {
    console.error("Error:", error);
    alert("❌ Error: " + error.message);
  }
});

function displayResults(results) {
  resultsTable.innerHTML = `
    <tr>
      <th>Description</th>
      <th>SKU</th>
      <th>Barcode</th>
      <th>Unit</th>
      <th>Match</th>
    </tr>
  `;

  results.forEach((result, index) => {
    console.log(`Displaying result for query '${result.query}':`, result.matches);
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${result.query}</td>
      <td id="sku-${index}">${result.id}</td>
      <td id="barcode-${index}">N/A</td>
      <td id="unit-${index}">N/A</td>
      <td>
        <select id="match-${index}" onchange="handleMatchChange(${index}, this)">
          <option value="">Select a match</option>
          ${result.matches.map((match, i) => `
            <option value="${match.document.name}" data-id="${match.document.id}" data-barcode="${match.document.barcode}" data-unit="${match.document.unit}">
              ${match.document.name}
            </option>
          `).join("")}
        </select>
      </td>
    `;
    resultsTable.appendChild(row);
  });

  confirmBtn.style.display = "inline-block";
}

function handleMatchChange(index, selectElement) {
  const query = resultsTable.rows[index + 1].cells[0].textContent;
  const matched = selectElement.value;
  const selectedOption = selectElement.options[selectElement.selectedIndex];
  const selectedId = selectedOption ? selectedOption.getAttribute("data-id") : null;
  const selectedBarcode = selectedOption ? selectedOption.getAttribute("data-barcode") : null;
  const selectedUnit = selectedOption ? selectedOption.getAttribute("data-unit") : null;

  const skuCell = document.getElementById(`sku-${index}`);
  const barcodeCell = document.getElementById(`barcode-${index}`);
  const unitCell = document.getElementById(`unit-${index}`);

  if (selectedId) {
    skuCell.textContent = selectedId;
    barcodeCell.textContent = selectedBarcode || "N/A";
    unitCell.textContent = selectedUnit || "N/A";
  } else {
    skuCell.textContent = searchResults[index].id;
    barcodeCell.textContent = "N/A";
    unitCell.textContent = "N/A";
  }

  if (matched) {
    selectedMatches[query] = matched;
  } else {
    delete selectedMatches[query];
  }
  console.log("Current selected matches:", selectedMatches);
}

confirmBtn.addEventListener("click", async () => {
  if (Object.keys(selectedMatches).length === 0) {
    alert("❗ Vui lòng chọn ít nhất một kết quả.");
    return;
  }

  try {
    const res = await fetch("http://209.124.85.88:5000/save-mapping", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(selectedMatches),
    });

    if (res.ok) {
      alert("✅ Đã lưu các mapping thành công!");
      confirmBtn.style.display = "none";
      resultsTable.innerHTML = `
        <tr>
          <th>Description</th>
          <th>SKU</th>
          <th>Barcode</th>
          <th>Unit</th>
          <th>Match</th>
        </tr>
      `;
      selectedMatches = {};
      fileInput.value = "";
    } else {
      const errorData = await res.json();
      alert(`❌ Lỗi khi lưu: ${errorData.error || "Lỗi không xác định"}`);
    }
  } catch (error) {
    console.error("Save mapping error:", error);
    alert("❌ Lỗi khi lưu: Lỗi mạng");
  }
});