document.addEventListener('DOMContentLoaded', () => {
    fetchMasterClasses();
});

async function fetchMasterClasses() {
    const container = document.getElementById('master-class-selection-container');
    try {
        const response = await fetch('master_classes.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const classes = await response.json();
        displayMasterClasses(classes);
    } catch (error) {
        console.error('Error fetching master classes:', error);
        if (container) {
            container.innerHTML = '<p class="error">Failed to load Master Classes. Please check the console for details.</p>';
        }
    }
}

function displayMasterClasses(classes) {
    const container = document.getElementById('master-class-selection-container');
    if (!container) return;

    container.innerHTML = ''; // Clear loading message

    // Group classes by day
    const classesByDay = classes.reduce((acc, cls) => {
        const day = cls.day || 'Unknown Day';
        if (!acc[day]) {
            acc[day] = [];
        }
        acc[day].push(cls);
        return acc;
    }, {});

    // Sort classes within each day by time
    for (const day in classesByDay) {
        classesByDay[day].sort((a, b) => {
            const timeA = a.time || '00:00';
            const timeB = b.time || '00:00';
            return timeA.localeCompare(timeB);
        });
    }

    // Generate HTML
    Object.keys(classesByDay).sort().forEach(day => { // Sort days alphabetically
        const daySection = document.createElement('div');
        daySection.classList.add('day-section');

        const dayHeader = document.createElement('h3');
        dayHeader.textContent = day;
        daySection.appendChild(dayHeader);

        const classList = document.createElement('ul');
        classList.classList.add('master-class-list');

        classesByDay[day].forEach((cls, index) => {
            const listItem = document.createElement('li');
            const checkboxId = `mc-checkbox-${day.replace(/\s+/g, '-')}-${index}`; // Create a unique ID

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = checkboxId;
            checkbox.value = JSON.stringify({ title: cls.title, presenter: cls.presenter, link: cls.link }); // Store identifying info
            checkbox.dataset.classInfo = JSON.stringify(cls); // Store all class info if needed later
            checkbox.addEventListener('change', handleSelectionChange);

            const label = document.createElement('label');
            label.htmlFor = checkboxId;
            label.textContent = `${cls.time} - ${cls.presenter}: ${cls.title}`;

            listItem.appendChild(checkbox);
            listItem.appendChild(label);
            classList.appendChild(listItem);
        });

        daySection.appendChild(classList);
        container.appendChild(daySection);
    });
}

function handleSelectionChange(event) {
    const selectedClasses = getSelectedClasses();
    console.log("Selected Master Classes:", selectedClasses);
    // In the future, this function will trigger the filtering of wine recommendations
    // For now, just logging the selection.
}

function getSelectedClasses() {
    const selected = [];
    const checkboxes = document.querySelectorAll('#master-class-selection-container input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        try {
            // Push the basic identifying info stored in the value
            selected.push(JSON.parse(checkbox.value));
            // Or if you need all info including wines:
            // selected.push(JSON.parse(checkbox.dataset.classInfo));
        } catch (e) {
            console.error("Error parsing class info from checkbox:", e, checkbox);
        }
    });
    return selected;
} 