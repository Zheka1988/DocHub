/* global django, jQuery */
(function () {
    'use strict';

    function init() {
        var $ = (window.django && window.django.jQuery) || window.jQuery || window.$;

        if (!$) {
            setTimeout(init, 1000);
            return;
        }

        $(document).ready(function () {

            // Function to sync parent task to child task_filter
            function syncTask(parentRow) {
                // Try to find the task widget.
                var taskSelect = parentRow.find('.field-task select');

                if (taskSelect.length === 0) {
                    taskSelect = parentRow.find('.field-task input[type="hidden"]');
                }
                if (taskSelect.length === 0) {
                    taskSelect = parentRow.find('.field-task input').first();
                }

                if (taskSelect.length === 0) {
                    return;
                }

                var selectedTaskId = taskSelect.val();

                // Find all child inline rows (DocumentSubTask) within this parent row
                var childRows = parentRow.find('.djn-group-nested .djn-item');

                childRows.each(function () {
                    var childRow = $(this);
                    // Find hidden task_filter input
                    var taskFilterInput = childRow.find('.field-task_filter input');
                    if (taskFilterInput.length > 0) {
                        // Check if value changed to avoid redundant events
                        if (taskFilterInput.val() !== selectedTaskId) {
                            taskFilterInput.val(selectedTaskId);
                            // Trigger change for smart-selects to pick it up
                            taskFilterInput.trigger('change');
                        }
                    }
                });
            }

            // Initial sync
            $('.djn-group-root > .djn-items > .djn-item').each(function () {
                syncTask($(this));
            });

            // Listen for changes on parent task select
            $(document).on('change select2:select', '.field-task select', function () {
                var parentRow = $(this).closest('.djn-item');
                syncTask(parentRow);
            });

            // Listen for new rows added (both parent and child)
            $(document).on('djn:added', function (event, $row, type) {
                if (type === 'inline') {
                    if ($row.find('.field-task_filter').length > 0) {
                        var parentRow = $row.closest('.djn-item.djn-level-1');
                        if (parentRow.length === 0) {
                            parentRow = $row.parents('.djn-item').first();
                        }
                        syncTask(parentRow);
                    }
                }
            });
        });
    }

    window.addEventListener('load', init);

})();
