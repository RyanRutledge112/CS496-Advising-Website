document.addEventListener("DOMContentLoaded", function () {
    const degreeSelect = document.getElementById("degreeSelect");

    degreeSelect.addEventListener("change", function() {
      const selectedOptions = [...degreeSelect.selectedOptions];

      if (selectedOptions.length > 6) {
        alert("You can select up to only 6 degrees.");
        selectedOptions[selectedOptions.length - 1].selected = false;
      }
    });
    // no more than 6 degrees selected
    const form = document.querySelector('form');
    form.addEventListener('submit', function(event) {
      const selectedOptions = [...degreeSelect.selectedOptions];
      if (selectedOptions.length > 6) {
        event.preventDefault();  // Prevent form submission
        alert("You can select up to only 6 degrees.");
      }
    });

    $('#degreeSelect').select2({
      placeholder: "Select degrees",
      allowClear: true,
      width: '100%'
    });
  });
  function filterDegrees() {
    let input = document.getElementById("degreeSearch").value.toLowerCase();
    let select = document.getElementById("degrees");
    let options = select.getElementsByTagName("option");

    for (let i = 0; i < options.length; i++) {
        let text = options[i].innerText.toLowerCase();
        if (text.includes(input)) {
            options[i].style.display = "";
        } else {
            options[i].style.display = "none";
        }
    }
  }

  function showPassInfo() {
    alert("Passwords must be at least 9 characters long, including an uppercase, number, and special character.");
}