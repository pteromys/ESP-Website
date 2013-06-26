$j(document).ready(function () {
	$j('form.qsd_buttons').each(function (i, b) {
		b = $j(b);
		var c = b.next('.qsd_content');

		// Some basic utilities
		var disableButtons = function () {
			b.add(c).find('input[type="submit"], input[type="button"], input[type="reset"]').prop('disabled', true);
		};
		var enableButtons = function () {
			b.add(c).find('input[type="submit"], input[type="button"], input[type="reset"]').prop('disabled', false);
		};
		var show_error = function (req, jquery_status, http_status) {
			alert(jquery_status + ": " + http_status + "\n" + req.responseText);
			enableButtons();
		};

		// All the event handlers
		var submitEditForm = function (e) {
			// Send edits to the server
			disableButtons();
			e.preventDefault();
			var f = $j(this);
			// Need a new URL
			new_url = f.find('input[name="url"]').val();
			// Prepare CSRF token
			refresh_csrf_cookie();
			$j.post(
				f.prop('action'),
				f.serialize() + '&csrfmiddlewaretoken=' + encodeURIComponent(csrf_token())
			).success(
				function (data, textStatus, jqXHR) {
					c.html(data);
					b.toggleClass('qsd_button_hidden');
					b.attr('action', new_url.replace(/\.html$/, '.edit.html'));
					enableButtons();
				}
			).fail(show_error);
		};
		var deleteQSD = function (e) {
			// Page deletion
			var url = b.attr('action').replace(/\.edit.html$/, '.html');
			// Require confirmation
			if (!confirm('Are you sure you want to delete\n' + url + '?')) { return; }
			disableButtons();
			// Prepare CSRF token
			refresh_csrf_cookie();
			$j.post(
				'/admin/qsd_fragment/delete/',
				{"url": url, "csrfmiddlewaretoken": csrf_token()}
			).success(
				function (data, textStatus, jqXHR) {
					c.text(data);
					b.css({display: 'none'});
					enableButtons();
				}
			).fail(show_error);
		};
		var cancelEdit = function (e) {
			// Cancel editing
			disableButtons();
			e.preventDefault();
			$j.get(
				'/admin/qsd_fragment/html/',
				{url: b.attr('action').replace(/\.edit.html$/, '.html')}
			).success(
				function (data, textStatus, jqXHR) {
					c.html(data);
					b.removeClass('qsd_button_hidden');
					enableButtons();
				}
			).fail(show_error);
		};
		b.on('submit', function (e) {
			// Request editing form
			disableButtons();
			e.preventDefault();
			$j.get(
				'/admin/qsd_fragment/form/',
				{url: b.attr('action').replace(/\.edit\.html$/, '.html')}
			).success(
				function (data, textStatus, jqXHR) {
					var f = $j(data);
					// Make slidey pages
					$j('<div>').append(f.children('ul')).wrap('<div class="slidey">').parent().appendTo(f);
					f.find('ul > li > a').on('click', function (e) {
						e.preventDefault();
						f.find('div.slidey > div').toggleClass('pagetwo');
					});
					// Attach event handlers and update display
					f.on('submit', submitEditForm);
					f.find('input[name="delete"]').on('click', deleteQSD);
					f.find('input[name="cancel"]').on('click', cancelEdit);
					b.toggleClass('qsd_button_hidden');
					c.empty().append(f);
					enableButtons();
				}
			).fail(show_error);
		}).on('reset', cancelEdit);
	});
});
