const searchInput = document.querySelector(".hero-search-input");
const suggestedLocations = document.querySelector(".suggested-locations");
const searchForm = document.querySelector(".hero-search-box");
const locationIdInput = document.querySelector("#location-id");

let selectedLocation = null;
let suggestions = [];
let debounceTimer;

if (searchInput && suggestedLocations) {
    searchInput.addEventListener("input", (event) => {
        const query = event.target.value.trim();

        selectedLocation = null;
        locationIdInput.value = "";

        clearTimeout(debounceTimer);

        debounceTimer = setTimeout(async () => {
            if (!query) {
                suggestions = [];
                renderSuggestions();
                return;
            }

            try {
                const response = await fetch(
                    `/api/v1/locations/autocomplete?search=${encodeURIComponent(query)}`
                );

                if (!response.ok) {
                    throw new Error(`Autocomplete failed: ${response.status}`);
                }

                const data = await response.json();

                suggestions = data.results || [];

                console.log("Suggestions:", suggestions);

                renderSuggestions();
            } catch (error) {
                console.error(error);
            }
        }, 300);
    });
}


function renderSuggestions() {
    suggestedLocations.innerHTML = "";

    if (suggestions.length === 0) {
        suggestedLocations.style.display = "none";
        return;
    }

    suggestedLocations.style.display = "block";

    suggestions.forEach((suggestion) => {
        const city = document.createElement("div");

        city.classList.add("suggested-city");

        city.textContent = suggestion.name;

        city.addEventListener("click", () => {
            searchInput.value = suggestion.name;

            selectedLocation = suggestion;
            locationIdInput.value = suggestion.id;

            suggestedLocations.innerHTML = "";
            suggestedLocations.style.display = "none";

            console.log("Selected:", selectedLocation);
        });

        suggestedLocations.appendChild(city);
    });
}


searchForm.addEventListener("submit", (event) => {
    if (!selectedLocation) {
        event.preventDefault();
        searchInput.focus();
        return;
    }

    // only location_id is sent, not the typed text
    searchInput.disabled = true;
});