  document.addEventListener("DOMContentLoaded", function () {
    const degreeSelect = document.getElementById("degreeSelect");

    degreeSelect.addEventListener("change", function() {
      const selectedOptions = [...degreeSelect.selectedOptions];
    });

    $('#degreeSelect').select2({
      placeholder: "Select degree",
      allowClear: true,
      width: '100%'
    });
  });

function filterDegrees() {
    let input = document.getElementById("degreeSearch").value.toLowerCase();
    let select = document.getElementById("degrees");
    let optgroups = select.getElementsByTagName("optgroup");

    for (let optgroup of optgroups) {
        let options = optgroup.getElementsByTagName("option");
        let visibleOption = false;

        for (let option of options) {
            let text = option.innerText.toLowerCase();
            if (text.includes(input)) {
                option.style.display = "";
                visibleOption = true;
            } else {
                option.style.display = "none";
            }
        }

        // Hide optgroup if it has no visible options
        optgroup.style.display = visibleOption ? "" : "none";
    }
}