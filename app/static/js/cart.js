document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll(".btn-cart-icon");

  buttons.forEach((button) => {
    button.addEventListener("click", function () {
      const productId = this.dataset.productId;
      const isAuthenticated = this.dataset.auth === "true";

      if (!isAuthenticated) {
        alert("Чтобы добавить товар в корзину, нужно авторизоваться.");
        return;
      }

      // Защита от повторного клика
      if (this.disabled) return;
      this.disabled = true;

      fetch("/cart/add", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ product_id: productId }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            const parent = this.parentElement;
            const productId = this.dataset.productId;

            const newBlock = document.createElement("div");
            newBlock.classList.add("cart-quantity", "ms-3");
            newBlock.dataset.productId = productId;
            newBlock.innerHTML = `
              <button class="qty-btn minus">−</button>
              <span class="qty-count">${data.quantity}</span>
              <button class="qty-btn plus">+</button>
            `;

            parent.replaceChild(newBlock, this);
          } else {
            alert(data.message || "Ошибка добавления в корзину.");
          }
        })
        .catch(() => {
          alert("Ошибка сервера.");
        })
        .finally(() => {
          this.disabled = false;
        });
    });
  });

  // ✅ Глобальный слушатель на document — для "+" и "-"
  document.addEventListener("click", function (e) {
    const plusBtn = e.target.closest(".qty-btn.plus");
    const minusBtn = e.target.closest(".qty-btn.minus");

    if (!plusBtn && !minusBtn) return;

    const container = (plusBtn || minusBtn).closest(".cart-quantity");
    const productId = container.dataset.productId;
    const countSpan = container.querySelector(".qty-count");
    let quantity = parseInt(countSpan.textContent);

    if (plusBtn) {
      quantity++;
    } else if (minusBtn) {
      quantity--;
    }

    fetch("/cart/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ product_id: productId, quantity }),
    })
      .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            if (quantity === 0) {
              // Если находимся в корзине профиля — отправить форму удаления
              const cartItem = container.closest('.cart-profile-item');
              if (cartItem) {
                const deleteForm = cartItem.querySelector('form');
                if (deleteForm) {
                  deleteForm.submit();
                  return;
                }
              }

              // Если не в корзине профиля — поведение по умолчанию (оставляем старую логику)
              const newBtn = document.createElement("button");
              newBtn.className = "btn btn-cart-icon ms-3";
              newBtn.dataset.productId = productId;
              newBtn.dataset.auth = "true";
              newBtn.style = "background: none; border: none; padding: 0;";
              newBtn.innerHTML = '<i class="icofont-cart cart-icon"></i>';

              container.parentElement.replaceChild(newBtn, container);
            } else {
              countSpan.textContent = quantity;

              // 🔁 Добавь вот этот блок для обновления ×2 возле картинки
              const qtyLabel = document.querySelector(`.cart-qty-label[data-product-id="${productId}"]`);
              if (qtyLabel) {
                qtyLabel.textContent = `×${quantity}`;
              }
            }
          } else {
            alert(data.message || "Ошибка обновления количества.");
          }
        })

      .catch(() => {
        alert("Ошибка сервера.");
      });
  });
});

// CSRF helper
function getCSRFToken() {
  const csrfToken = document.querySelector("meta[name='csrf-token']");
  return csrfToken ? csrfToken.getAttribute("content") : "";
}
