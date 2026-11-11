import unittest
from unittest.mock import patch

import server


class ChatHistoryTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_clean_client_history_filters_and_limits(self):
        raw = [
            {"role": "system", "text": "ignore"},
            {"role": "user", "text": "  Bonjour  "},
            {"role": "assistant", "text": "Salut"},
            {"role": "user", "text": 123},
        ]
        self.assertEqual(
            server.clean_client_history(raw),
            [
                {"role": "user", "text": "Bonjour"},
                {"role": "assistant", "text": "Salut"},
            ],
        )

    @patch("server.current_user", return_value=None)
    def test_history_requires_authenticated_user(self, _current_user):
        response = self.client.get("/historique")
        self.assertEqual(response.status_code, 401)

    @patch("server.bearer_token", return_value="test-token")
    @patch("server.supabase_data_request", return_value=[
        {"messages": [{"role": "user", "text": "Mon historique privé"}]}
    ])
    @patch("server.current_user", return_value={"id": "user-123"})
    def test_get_history_returns_authenticated_users_rows(
        self, _current_user, data_request, _token
    ):
        response = self.client.get("/historique")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["messages"],
            [{"role": "user", "text": "Mon historique privé"}],
        )
        self.assertIn("user_id=eq.user-123", data_request.call_args.args[0])

    @patch("server.bearer_token", return_value="test-token")
    @patch("server.supabase_data_request", return_value={})
    @patch("server.current_user", return_value={"id": "user-123"})
    def test_save_history_calls_user_scoped_rpc(
        self, _current_user, data_request, _token
    ):
        response = self.client.put(
            "/historique",
            json={
                "messages": [
                    {"role": "user", "text": "Question"},
                    {"role": "assistant", "text": "Réponse"},
                    {"role": "system", "text": "ne pas enregistrer"},
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 2)
        self.assertEqual(
            data_request.call_args.kwargs["payload"],
            {
                "p_messages": [
                    {"role": "user", "text": "Question"},
                    {"role": "assistant", "text": "Réponse"},
                ]
            },
        )


if __name__ == "__main__":
    unittest.main()
