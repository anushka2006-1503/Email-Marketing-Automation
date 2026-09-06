import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for

import models

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")


@contacts_bp.route("/")
def list_contacts():
    search = request.args.get("q", "").strip()
    contacts = models.list_contacts(search)
    return render_template("contacts/list.html", contacts=contacts, search=search)


@contacts_bp.route("/add", methods=["GET", "POST"])
def add_contact():
    if request.method == "POST":
        try:
            models.create_contact(
                request.form.get("name", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("company", ""),
                request.form.get("notes", ""),
            )
            flash("Contact added.", "success")
            return redirect(url_for("contacts.list_contacts"))
        except sqlite3.IntegrityError:
            flash("That email is already in your contact list.", "danger")
    return render_template("contacts/form.html", contact=None, title="Add contact")


@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
def edit_contact(contact_id):
    contact = models.get_contact(contact_id)
    if not contact:
        flash("Contact not found.", "danger")
        return redirect(url_for("contacts.list_contacts"))
    if request.method == "POST":
        try:
            models.update_contact(
                contact_id,
                request.form.get("name", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("company", ""),
                request.form.get("notes", ""),
            )
            flash("Contact updated.", "success")
            return redirect(url_for("contacts.list_contacts"))
        except sqlite3.IntegrityError:
            flash("That email is already used by another contact.", "danger")
    return render_template("contacts/form.html", contact=contact, title="Edit contact")


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    models.delete_contact(contact_id)
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts.list_contacts"))
