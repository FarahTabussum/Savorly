document.addEventListener("DOMContentLoaded", function() {
  // Flash messages: dismiss via cross button, and auto-hide after a few seconds
  document.querySelectorAll(".message-stack .site-alert").forEach(function(alert) {
    var timer = setTimeout(dismiss, 2000);

    function dismiss() {
      clearTimeout(timer);
      alert.classList.add("site-alert--leaving");
      setTimeout(function() {
        alert.remove();
        var stack = document.querySelector(".message-stack");
        if (stack && !stack.children.length) stack.remove();
      }, 220);
    }

    var closeBtn = alert.querySelector("[data-dismiss-message]");
    if (closeBtn) closeBtn.addEventListener("click", dismiss);
  });

  // Password toggle
  document.querySelectorAll("[data-password-toggle]").forEach(function(button) {
    button.addEventListener("click", function() {
      var input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      var shouldShow = input.type === "password";
      input.type = shouldShow ? "text" : "password";
      button.textContent = shouldShow ? "Hide" : "Show";
    });
  });

  // Ingredient search on the Chef's Table: show recipes whose description
  // contains at least two of the typed ingredients.
  var searchInput = document.getElementById("ingredient-search");
  if (searchInput) {
    var searchCount = document.getElementById("search-count");
    var tbody = document.getElementById("chefs-table-body");
    var recipeRows = tbody ? Array.prototype.slice.call(tbody.querySelectorAll("tr[data-description]")) : [];
    var noResultsRow = tbody ? tbody.querySelector(".chefs-table__no-results-row") : null;
    var emptyRow = tbody ? tbody.querySelector(".chefs-table__empty-row") : null;

    searchInput.addEventListener("input", function() {
      // Split on commas/whitespace, lowercase, drop empties
      var ingredients = searchInput.value
        .toLowerCase()
        .split(/[\s,]+/)
        .filter(function(word) { return word.length > 0; });

      var visible = 0;
      recipeRows.forEach(function(row) {
        var words = (row.dataset.description || "")
          .toLowerCase()
          .split(/[^a-z0-9]+/)
          .filter(function(word) { return word.length > 0; });
        var matches = 0;
        ingredients.forEach(function(ing) {
          if (words.indexOf(ing) !== -1) matches++;
        });
        var show = ingredients.length === 0 || matches >= 2;
        row.style.display = show ? "" : "none";
        if (show) visible++;
      });

      if (noResultsRow) noResultsRow.hidden = !(ingredients.length > 0 && visible === 0);
      if (emptyRow) {
        emptyRow.style.display =
          ingredients.length === 0 && recipeRows.length === 0 ? "" : "none";
      }

      if (searchCount) {
        if (ingredients.length === 0) {
          searchCount.textContent = "";
        } else if (visible === 0) {
          searchCount.textContent = "No recipes match those ingredients.";
        } else {
          searchCount.textContent =
            visible + " of " + recipeRows.length + " recipes match your ingredients.";
        }
      }
    });
  }

  // Notification badge
  var badge = document.getElementById("notification-badge");
  if (badge) {
    fetch("/api/notifications/unread-count/")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.count > 0) {
          badge.textContent = data.count > 99 ? "99+" : data.count;
          badge.style.display = "grid";
        }
      });
  }

  // Helper: get CSRF token
  function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]").value;
  }

  // Helper: get recipe ID
  function getRecipeId() {
    return document.querySelector("[data-recipe-id]").dataset.recipeId;
  }

  // Like/Unlike
  var likeBtn = document.getElementById("like-button");
  if (likeBtn) {
    likeBtn.addEventListener("click", function() {
      var action = likeBtn.dataset.action;

      fetch("/recipes/" + getRecipeId() + "/", {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken()
        },
        body: new URLSearchParams({ action: action })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        document.getElementById("like-count").textContent =
          data.likes_count + " like" + (data.likes_count !== 1 ? "s" : "");
        if (data.user_has_liked) {
          likeBtn.classList.add("like-button--active");
          likeBtn.dataset.action = "unlike";
          likeBtn.querySelector("svg").setAttribute("fill", "currentColor");
        } else {
          likeBtn.classList.remove("like-button--active");
          likeBtn.dataset.action = "like";
          likeBtn.querySelector("svg").setAttribute("fill", "none");
        }
      });
    });
  }

  // Build a comment/reply card from a server response
  function buildCommentCard(comment, isReply) {
    var card = document.createElement("div");
    card.className = "comment-card" + (isReply ? " comment-card--reply" : "");
    card.id = "comment-" + comment.id;

    var header = document.createElement("div");
    header.className = "comment-header";

    var authorWrap = document.createElement("span");
    authorWrap.className = "comment-author";
    var author = document.createElement("strong");
    author.textContent = comment.username;
    authorWrap.appendChild(author);
    if (comment.is_recipe_chef) {
      var chefBadge = document.createElement("span");
      chefBadge.className = "comment-chef-badge";
      chefBadge.textContent = "chef";
      authorWrap.appendChild(chefBadge);
    }

    var time = document.createElement("span");
    time.className = "comment-time";
    time.textContent = comment.created_at;
    header.appendChild(authorWrap);
    header.appendChild(time);

    var body = document.createElement("p");
    body.className = "comment-text";
    body.textContent = comment.text;

    var actions = document.createElement("div");
    actions.className = "comment-actions";
    if (!isReply) {
      var reply = document.createElement("button");
      reply.type = "button";
      reply.className = "comment-reply-btn";
      reply.dataset.commentId = comment.id;
      reply.textContent = "Reply";
      actions.appendChild(reply);
    }
    if (comment.can_delete) {
      var del = document.createElement("button");
      del.type = "button";
      del.className = "comment-delete";
      del.dataset.commentId = comment.id;
      del.textContent = "Delete";
      actions.appendChild(del);
    }

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);

    // Top-level cards also need an (initially hidden) reply form so the user
    // can reply to comments they just posted without refreshing.
    if (!isReply) {
      var replyForm = document.createElement("div");
      replyForm.className = "reply-form";
      replyForm.dataset.replyForm = comment.id;
      replyForm.hidden = true;

      var replyTa = document.createElement("textarea");
      replyTa.rows = 2;
      replyTa.maxLength = 1000;
      replyTa.placeholder = "Reply to " + comment.username + "...";

      var replyActions = document.createElement("div");
      replyActions.className = "reply-form__actions";

      var replySubmit = document.createElement("button");
      replySubmit.type = "button";
      replySubmit.className = "btn btn-primary reply-submit";
      replySubmit.textContent = "Post Reply";

      var replyCancel = document.createElement("button");
      replyCancel.type = "button";
      replyCancel.className = "reply-cancel";
      replyCancel.textContent = "Cancel";

      replyActions.appendChild(replySubmit);
      replyActions.appendChild(replyCancel);
      replyForm.appendChild(replyTa);
      replyForm.appendChild(replyActions);
      card.appendChild(replyForm);
    }

    return card;
  }

  function bumpCommentCount(delta) {
    var el = document.getElementById("comment-count");
    if (!el) return;
    var next = Math.max(0, parseInt(el.textContent, 10) + delta);
    el.textContent = next;
    if (next === 0) {
      document.getElementById("comments-list").innerHTML =
        '<p class="comments-empty" id="comments-empty">No comments yet. Be the first to share your thoughts!</p>';
    }
  }

  function postComment(fields, onSuccess) {
    var body = new URLSearchParams(fields);
    fetch("/recipes/" + getRecipeId() + "/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken()
      },
      body: body
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) return;
      onSuccess(data.comment);
    });
  }

  // Top-level comment submission
  var commentSubmit = document.getElementById("comment-submit");
  if (commentSubmit) {
    commentSubmit.addEventListener("click", function() {
      var textarea = document.getElementById("comment-text");
      var text = textarea.value.trim();
      if (!text) return;

      postComment({ action: "comment", comment_text: text }, function(comment) {
        var list = document.getElementById("comments-list");
        var empty = document.getElementById("comments-empty");
        if (empty) empty.remove();

        list.prepend(buildCommentCard(comment, false));
        bumpCommentCount(1);
        textarea.value = "";
      });
    });
  }

  // Reply / Cancel / Post-reply (event delegation)
  document.addEventListener("click", function(e) {
    var openBtn = e.target.closest(".comment-reply-btn");
    if (openBtn) {
      var form = document.querySelector('[data-reply-form="' + openBtn.dataset.commentId + '"]');
      if (!form) return;
      var isOpen = !form.hidden;
      // close any other open reply form first
      document.querySelectorAll(".reply-form").forEach(function(f) { f.hidden = true; });
      form.hidden = isOpen;
      if (!isOpen) form.querySelector("textarea").focus();
      return;
    }

    var cancelBtn = e.target.closest(".reply-cancel");
    if (cancelBtn) {
      cancelBtn.closest(".reply-form").hidden = true;
      return;
    }

    var submitBtn = e.target.closest(".reply-submit");
    if (submitBtn) {
      var replyForm = submitBtn.closest(".reply-form");
      var replyText = replyForm.querySelector("textarea");
      var parentId = replyForm.dataset.replyForm;
      var text = replyText.value.trim();
      if (!text) return;

      submitBtn.disabled = true;
      postComment(
        { action: "comment", comment_text: text, parent_id: parentId },
        function(comment) {
          submitBtn.disabled = false;
          replyText.value = "";
          replyForm.hidden = true;

          var parentCard = document.getElementById("comment-" + parentId);
          if (!parentCard) return;
          var replies = parentCard.querySelector(".comment-replies");
          if (!replies) {
            replies = document.createElement("div");
            replies.className = "comment-replies";
            parentCard.insertBefore(replies, replyForm);
          }
          replies.appendChild(buildCommentCard(comment, true));
          bumpCommentCount(1);
        }
      );
    }
  });

  // Delete comment (event delegation)
  document.addEventListener("click", function(e) {
    var btn = e.target.closest(".comment-delete");
    if (!btn) return;

    var commentId = btn.dataset.commentId;

    fetch("/recipes/" + getRecipeId() + "/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken()
      },
      body: new URLSearchParams({ action: "delete_comment", comment_id: commentId })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.deleted) {
        var card = document.getElementById("comment-" + data.id);
        if (card) card.remove();
        bumpCommentCount(-(data.removed || 1));
      }
    });
  });

  // Delete a notification (cross button on notifications page)
  document.addEventListener("click", function(e) {
    var btn = e.target.closest(".notification-dismiss");
    if (!btn) return;

    btn.disabled = true;
    fetch("/notifications/delete/" + btn.dataset.notificationId + "/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken()
      }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.deleted) { btn.disabled = false; return; }

      var card = document.getElementById("notification-" + data.id);
      if (card) card.remove();

      // Keep the navbar badge in sync
      var badge = document.getElementById("notification-badge");
      if (badge) {
        if (data.unread_count > 0) {
          badge.textContent = data.unread_count > 99 ? "99+" : data.unread_count;
          badge.style.display = "grid";
        } else {
          badge.style.display = "none";
        }
      }

      // Show the empty state when the last notification is removed
      var list = document.querySelector(".notifications-list");
      if (list && !list.querySelector(".notification-card")) {
        list.innerHTML =
          '<div class="notifications-empty"><span aria-hidden="true">🔔</span>' +
          "<p>No notifications yet. When someone likes or comments on your recipes, " +
          "you'll see it here.</p></div>";
      }
    })
    .catch(function() { btn.disabled = false; });
  });

  // Clicking a notification card marks it as read (AJAX) and opens the recipe
  document.addEventListener("click", function(e) {
    var dismiss = e.target.closest(".notification-dismiss");
    if (dismiss) return; // handled above

    var card = e.target.closest(".notification-card");
    if (!card) return;

    var id = card.dataset.notificationId;
    var url = card.dataset.recipeUrl;

    // Mark as read without a page refresh; badge stays in sync
    fetch("/notifications/mark-read/" + id + "/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken()
      }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.read) return;
      card.classList.remove("notification-card--unread");

      var badge = document.getElementById("notification-badge");
      if (badge) {
        if (data.unread_count > 0) {
          badge.textContent = data.unread_count > 99 ? "99+" : data.unread_count;
          badge.style.display = "grid";
        } else {
          badge.style.display = "none";
        }
      }
    })
    .catch(function() {});

    // Navigate to the recipe (the read state is already persisted)
    window.location.href = url;
  });
});
