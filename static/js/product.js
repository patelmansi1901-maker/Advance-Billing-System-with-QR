
document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("productSearch");
    const productTable = document.getElementById("productTable");

    if (searchInput && productTable) {

        searchInput.addEventListener("keyup", function () {

            const searchValue = searchInput.value.toLowerCase();

            const rows = productTable.querySelectorAll("tbody tr");

            rows.forEach(function (row) {

                const productName = row.cells[1].textContent.toLowerCase();
                const category = row.cells[2].textContent.toLowerCase();

                if (
                    productName.includes(searchValue) ||
                    category.includes(searchValue)
                ) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }

            });

        });

    }

});
