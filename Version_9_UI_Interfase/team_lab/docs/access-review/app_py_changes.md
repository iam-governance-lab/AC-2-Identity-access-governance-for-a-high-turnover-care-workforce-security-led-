# Changes required in app/app.py

## 1 Add imports

Add these imports after the existing `database` imports:

```python
from access_review import build_access_review_blueprint
from access_review_db import initialize_access_review_database
```

## 2 Initialise the new schema

Immediately after the existing `initialize_database()` call, add:

```python
initialize_access_review_database()
```

## 3 Register the Blueprint

Insert this block after the complete `require_roles` function and before the
first `@app.route` declaration. The functions passed to the Blueprint are the
same validated identity, active-session, RBAC and audit functions already used
by the existing portal.

```python
app.register_blueprint(
    build_access_review_blueprint(
        auth=auth,
        require_active_session=require_active_session,
        require_roles=require_roles,
        identity_from_context=identity_from_context,
        write_audit_event=write_audit_event,
    )
)
```

## 4 Replace the old review placeholder

The current `/review` route can remain as a backward-compatible redirect.
Replace its function body with this version:

```python
from flask import redirect, url_for


@app.route("/review")
@auth.login_required
@require_active_session
@require_roles("Manager", "Auditor")
def review(*, context):
    identity = identity_from_context(context)
    write_audit_event(
        identity,
        action="OPEN_REVIEW_REDIRECT",
        object_id="access-review",
        result="ALLOW",
    )
    return redirect(url_for("access_review.dashboard"))
```

If `redirect` and `url_for` are not already imported, add them to the existing
Flask import line.

## 5 Add a home-page link

Add this link to `app/templates/index.html`:

```html
{% set signed_in_roles = user.get("roles", []) %}
{% if "Manager" in signed_in_roles or "Auditor" in signed_in_roles %}
  <li><a href="{{ url_for('access_review.dashboard') }}">Access review</a></li>
{% endif %}
```

The route decorators remain the security control. Hiding the link is only a
usability feature.
