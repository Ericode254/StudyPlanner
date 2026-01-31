$(document).ready(function () {
    const converter = new showdown.Converter();

    const projectTypeOptions = {
        'Coding': 'Senior Engineer',
        'Art': 'Artist',
        'Art & craft': 'Craftsman',
        'Music': 'Musician',
        'Dance': 'Dancer',
        'Cooking': 'Chef',
        'Photography': 'Photographer',
        'Writing': 'Author',
        'Design': 'Designer',
        'Marketing': 'Marketing Specialist',
        'Finance': 'Financial Analyst',
        'Science': 'Scientist',
        'Mathematics': 'Mathematician',
        'History': 'Historian',
        'Philosophy': 'Philosopher'
    };

    const referencePreferanceOptions = {
        "Youtube (free)": "youtube", 
        "Video": "video", 
        "Book": "book", 
        "Text": "text", 
        "Combo": "youtube, video, text, book"
    };

    function createTimeDurationObject() {
        let durations = [];
        for (let i = 1; i <= 20; i++) durations.push({ key: `${i} hour${i > 1 ? 's' : ''}`, value: i });
        for (let i = 1; i <= 30; i++) durations.push({ key: `${i} day${i > 1 ? 's' : ''}`, value: i * 24 });
        for (let i = 1; i <= 9; i++) durations.push({ key: `${i} month${i > 1 ? 's' : ''}`, value: i * 30 * 24 });
        durations.sort((a, b) => a.value - b.value);
        return durations;
    }

    // Populate Dropdowns
    const projectTypeDropdown = $('#project_type_dropdown');
    if (projectTypeDropdown.length) {
        $.each(projectTypeOptions, function(key, value) {
            projectTypeDropdown.append($('<option>', { value: key.toLowerCase(), text: key }));
        });
    }

    const referencPreferenceDropDown = $("#reference_preference");
    if (referencPreferenceDropDown.length) {
        $.each(referencePreferanceOptions, function(key, value) {
            referencPreferenceDropDown.append($('<option>', { value: value, text: key }));
        });
    }

    const timeFrameDropdown = $("#timeframe");
    if (timeFrameDropdown.length) {
        const durations = createTimeDurationObject();
        durations.forEach(d => {
            timeFrameDropdown.append($('<option>', { value: d.key, text: d.key }));
        });
    }

    /** STUDY PLAN SUBMISSION */
    $('#studyPlanSubmitBtn').on('click', async function() {
        const $btn = $(this);
        const $spinner = $('#spinner');
        const form = document.getElementById('studyPlanForm');
        const formData = new FormData(form);

        // Simple validation
        const goal = formData.get('goal');
        if (!goal) {
            alert("Please enter a learning goal.");
            return;
        }

        try {
            $btn.prop('disabled', true);
            $spinner.removeClass('hidden');

            const response = await fetch('/study_plan_creator', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Something went wrong');
            }

            const html = converter.makeHtml(data.response);
            $('#studyPlanResponse').html(html);
            $('#studyPlanResponseContainer').removeClass('hidden');
            
            // Scroll to response
            $('html, body').animate({
                scrollTop: $("#studyPlanResponseContainer").offset().top - 100
            }, 500);

        } catch (error) {
            console.error(error);
            alert(error.message);
        } finally {
            $btn.prop('disabled', false);
            $spinner.addClass('hidden');
        }
    });
});