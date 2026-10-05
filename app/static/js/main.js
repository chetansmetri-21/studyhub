/* =========================================================
   STUDYHUB - BUTTON CLICK CIRCLE EFFECT
   ========================================================= */

(function () {
    "use strict";

    document.addEventListener("pointerdown", function (event) {

        /* Only show on buttons and clickable elements */
        const target = event.target.closest(
            "button, a, [role='button'], input[type='button'], input[type='submit'], select"
        );

        if (!target) {
            return;
        }

        const circle = document.createElement("span");

        circle.className = "sh-click-circle";

        circle.style.left = event.clientX + "px";
        circle.style.top = event.clientY + "px";

        document.body.appendChild(circle);

        setTimeout(function () {
            circle.remove();
        }, 650);

    }, { passive: true });

})();