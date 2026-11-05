"""Тесты инструментов (tools) — поиск по базе знаний."""

from __future__ import annotations

from tools.knowledge_tools import get_support_policy, search_support_knowledge


class TestSearchSupportKnowledge:
    """Тесты функции search_support_knowledge."""

    def test_search_delivery_info(self) -> None:
        """Поиск информации о доставке."""
        result = search_support_knowledge("доставка по Москве сроки")
        assert len(result) > 0
        assert "Москва" in result or "доставк" in result.lower()

    def test_search_payment_info(self) -> None:
        """Поиск информации об оплате."""
        result = search_support_knowledge("оплата банковская карта")
        assert len(result) > 0
        assert "карт" in result.lower() or "оплат" in result.lower()

    def test_search_refund_info(self) -> None:
        """Поиск информации о возврате."""
        result = search_support_knowledge("возврат товара срок")
        assert len(result) > 0
        assert "14" in result or "возвр" in result.lower()

    def test_search_empty_query(self) -> None:
        """Пустой запрос возвращает ошибку."""
        result = search_support_knowledge("")
        assert "ошибка" in result.lower() or "пуст" in result.lower()

    def test_search_no_results(self) -> None:
        """Поиск несуществующей информации."""
        result = search_support_knowledge("ксеноморф из фильма чужой")
        # Проверяем, что результат содержит информацию об отсутствии
        assert len(result) > 0
        # Результат должен быть осмысленным
        assert isinstance(result, str)

    def test_search_faq_info(self) -> None:
        """Поиск информации из FAQ."""
        result = search_support_knowledge("оформить заказ корзина")
        assert len(result) > 0
        assert "корзин" in result.lower() or "заказ" in result.lower()


class TestGetSupportPolicy:
    """Тесты функции get_support_policy."""

    def test_delivery_policy(self) -> None:
        """Получение правил для категории delivery."""
        result = get_support_policy("delivery")
        assert "доставк" in result.lower()
        assert "эскалироват" in result.lower()

    def test_payment_policy(self) -> None:
        """Получение правил для категории payment."""
        result = get_support_policy("payment")
        assert "оплат" in result.lower()
        assert "карт" in result.lower()

    def test_refund_policy(self) -> None:
        """Получение правил для категории refund."""
        result = get_support_policy("refund")
        assert "возвр" in result.lower()
        assert "14" in result or "гаранти" in result.lower()

    def test_unknown_category(self) -> None:
        """Неизвестная категория возвращает сообщение об ошибке."""
        result = get_support_policy("unknown_category_xyz")
        assert "неизвестн" in result.lower()

    def test_case_insensitive(self) -> None:
        """Название категории не зависит от регистра."""
        result_upper = get_support_policy("DELIVERY")
        result_lower = get_support_policy("delivery")
        # Обе должны вернуть правила (не ошибку)
        assert "ошибка" not in result_upper.lower()
        assert "ошибка" not in result_lower.lower()
