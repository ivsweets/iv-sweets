# TODO: Fix Admin Receiving Client Complaints

## Steps from Approved Plan

- [x] Step 1: Update `iv_sweets/iv_sweets/settings.py` to configure real SMTP email backend (e.g., Gmail) for admin notifications.
- [x] Step 2: Update `iv_sweets/sweets/views.py` to add missing `send_mail` import, enhance success message in `nova_reclamacao`, and improve email body with full details and admin link.
- [x] Step 3: Test the implementation by running the server, submitting a complaint as a client, and verifying admin receipt (email + dashboard list).
- [x] Step 4: Update this TODO.md with completion status after each step.

**Notes**: 
- For email: Use Gmail SMTP as example; replace placeholders with actual credentials (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD).
- No migrations needed.
- After changes, run `python manage.py runserver` to test.
