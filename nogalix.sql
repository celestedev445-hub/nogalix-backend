-- Nogalix database dump
-- Generated: 2026-08-28T14:42:33.279299+00:00
-- Database: nogalix

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `alembic_version` (`version_num`) VALUES ('0004_user_role');

DROP TABLE IF EXISTS `cvs`;
CREATE TABLE `cvs` (
  `id` varchar(36) NOT NULL,
  `user_id` int NOT NULL,
  `template_id` varchar(80) NOT NULL,
  `title` varchar(190) NOT NULL,
  `principal` tinyint(1) NOT NULL DEFAULT '0',
  `completion` int NOT NULL DEFAULT '0',
  `payload` json NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_cvs_user_id` (`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `cvs` (`id`, `user_id`, `template_id`, `title`, `principal`, `completion`, `payload`, `created_at`, `updated_at`) VALUES ('020bcc39-b3b0-441a-a29a-3e488741c79d', 1, 'atlas', 'CV Demo', 0, 55, '{"id": null, "title": "CV Demo", "skills": [], "summary": "Developpeuse passionnee avec plus de dix ans d experience en ingenierie logicielle.", "identity": {"email": "ada@example.com", "phone": "", "photo": null, "title": "Dev", "github": null, "website": null, "lastName": "Lovelace", "location": "", "firstName": "Ada"}, "projects": [], "education": [], "interests": null, "languages": [], "principal": false, "updatedAt": null, "completion": 0, "templateId": "atlas", "experiences": [], "certifications": []}', '2026-08-27 13:23:37', '2026-08-27 13:23:37');
INSERT INTO `cvs` (`id`, `user_id`, `template_id`, `title`, `principal`, `completion`, `payload`, `created_at`, `updated_at`) VALUES ('87fa42d1-00dd-47e1-9c58-f6076f32fed1', 3, 'atlas', 'CV1', 0, 55, '{"id": null, "title": "CV1", "skills": [], "summary": "Developpeur avec plus de dix ans d experience logicielle et projets concrets.", "identity": {"email": "plan.check.728179@example.com", "phone": "", "photo": null, "title": "Dev", "github": null, "website": null, "lastName": "B", "location": "", "firstName": "A"}, "projects": [], "education": [], "interests": null, "languages": [], "principal": false, "updatedAt": null, "completion": 0, "templateId": "atlas", "experiences": [], "certifications": []}', '2026-08-27 15:55:02', '2026-08-27 15:55:02');
INSERT INTO `cvs` (`id`, `user_id`, `template_id`, `title`, `principal`, `completion`, `payload`, `created_at`, `updated_at`) VALUES ('c8cc2421-2cb0-49fc-9294-1237c1624d14', 10, 'ndiaye', 'Nouveau CV', 0, 30, '{"id": "c8cc2421-2cb0-49fc-9294-1237c1624d14", "title": "Nouveau CV", "skills": [], "summary": "", "identity": {"email": "admin.demo@nogalix.com", "phone": "", "photo": null, "title": "", "github": "", "website": "", "lastName": "Nogalix08", "location": "", "firstName": "Admin"}, "projects": [], "education": [], "interests": [], "languages": [], "principal": false, "updatedAt": "2026-08-28T11:11:07.119Z", "completion": 23, "templateId": "ndiaye", "experiences": [], "editorStatus": "ready", "certifications": []}', '2026-08-28 11:10:52', '2026-08-28 11:11:08');

DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id` varchar(36) NOT NULL,
  `user_id` int NOT NULL,
  `type` varchar(80) NOT NULL,
  `kind` varchar(40) NOT NULL,
  `message` text NOT NULL,
  `href` varchar(255) DEFAULT NULL,
  `actor` varchar(120) DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `read_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_notifications_user_id` (`user_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('805716de-496e-40cb-a199-16c336eafdad', 1, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 13:23:37');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('fc927a8c-2e28-4294-b330-8c2213ac1d34', 1, 'cv', 'cv', 'CV « CV Demo » créé.', '/cv/020bcc39-b3b0-441a-a29a-3e488741c79d', 'Nogalix', 0, NULL, '2026-08-27 13:23:37');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('9405af65-33ac-4081-a680-cae3aea057eb', 2, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 13:29:56');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('328db653-c9bf-48e4-9e36-84966c66d30f', 2, 'cv', 'cv', 'CV « CV Smoke » créé.', '/cv/7e2d615e-9a9e-41df-ba72-ed1fce3872cd', 'Nogalix', 0, NULL, '2026-08-27 13:29:56');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('a58cc739-433f-45b9-b214-ef99ddf877bc', 2, 'analyse', 'analyse', 'Analyse du CV « CV Smoke » : score 72/100 (Bon).', '/analyse', 'Nogalix', 0, NULL, '2026-08-27 13:29:56');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('c39a4075-7e6a-4b13-9824-dae73abcd60a', 3, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 15:54:55');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('a9513e8f-1bc5-4765-ad99-24bbd6f5c480', 3, 'cv', 'cv', 'CV « CV1 » créé.', '/cv/87fa42d1-00dd-47e1-9c58-f6076f32fed1', 'Nogalix', 0, NULL, '2026-08-27 15:55:02');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('56f03e87-f361-497b-92d6-608f424fe56b', 4, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 15:55:02');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('a21f3a7d-2d3f-421d-a561-abc6c017635b', 5, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:16:29');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('d905bab1-dce4-4805-97f2-feeb33d2e764', 6, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:17:11');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('bb39d554-7653-4026-b217-1fc5d274392b', 7, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:17:51');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('5cf15cf6-2261-48d2-a74b-182cd1a417b6', 8, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:18:13');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('23796ecb-3e0b-44fb-a744-5146036b043a', 9, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:23:37');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('8013d1dc-a305-406f-a22f-6eb0bf62427d', 10, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-27 16:23:37');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('565f6684-a3f4-406b-aa45-f9cb31809b76', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/59740d54-bbe9-474c-aed6-1630c32aaaf7', 'Nogalix', 0, NULL, '2026-08-28 08:14:10');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('a5141fc1-1d10-4ab9-a079-cf77770d85d9', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/e63cc23e-e035-41a6-8be3-c8eae7fccb14', 'Nogalix', 1, '2026-08-28 09:11:41', '2026-08-28 09:10:09');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('186c023a-e1ef-4240-80df-2a1c20b69a0a', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/22528cec-c00d-4073-981a-9698aebba5f8', 'Nogalix', 0, NULL, '2026-08-28 09:12:54');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('683a3413-84cd-4434-883a-9c7314291c1d', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/3062c9a1-1237-45a5-905f-837837790b45', 'Nogalix', 0, NULL, '2026-08-28 09:34:21');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('9c63ac04-54fc-4822-a225-83a4be928a50', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/9124214d-466f-486f-9baf-6e508b641c27', 'Nogalix', 0, NULL, '2026-08-28 09:53:23');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('33c18b56-8999-47f7-970b-b5486ffeefd4', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/3d0fb226-32d6-429f-b807-ec4877f43db7', 'Nogalix', 0, NULL, '2026-08-28 10:14:05');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('505704e1-0e72-4133-b3ea-29eae489ee07', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/d6acef8f-a1ba-44a0-abae-ccabe8b38360', 'Nogalix', 0, NULL, '2026-08-28 10:15:32');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('0d4b920e-6f95-40bf-80da-d88534c35f78', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/f09d3663-421b-450d-b1c0-8310135566e7', 'Nogalix', 0, NULL, '2026-08-28 10:15:36');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('b4a60e45-210e-42de-a950-0f514cff12d7', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/15fb5f70-4641-4cb8-85d0-cb5760f88dd4', 'Nogalix', 0, NULL, '2026-08-28 10:19:13');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('4340b7e7-5911-4b6f-b898-2cc098bc19c5', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/9d5a04e4-afb6-4eef-b396-cdddcb71fbd4', 'Nogalix', 0, NULL, '2026-08-28 10:19:31');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('ccd151fe-b697-4a1a-8cb1-0b07c0f25f6e', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/f56c0f95-8e9c-483c-8a5c-040943589cae', 'Nogalix', 0, NULL, '2026-08-28 10:48:20');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('44cbebe4-984a-45a7-9a25-b62b8faa9045', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/947fec43-4163-4e2a-8acc-4fe2c9428cc0', 'Nogalix', 0, NULL, '2026-08-28 10:50:33');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('818e22ca-ba66-42dc-84cc-0bd71b60b18f', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/538bd611-0b89-4711-b085-146f0a260f15', 'Nogalix', 0, NULL, '2026-08-28 10:50:43');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('9dc40c7b-7a77-4cbf-a103-c9a30016bec2', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/796869ed-60a3-443a-a429-166eb40a865c', 'Nogalix', 0, NULL, '2026-08-28 10:53:30');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('e93cfb4c-d693-43af-b01c-ea6aa5c08cc0', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/9c603e6a-e54d-45b8-bfed-39140a431524', 'Nogalix', 0, NULL, '2026-08-28 10:56:33');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('21d8a4d5-7725-4a75-84d0-39180a730993', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/79905acd-1888-4704-a363-fd99a442bcf2', 'Nogalix', 0, NULL, '2026-08-28 11:01:53');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('6c582f69-38e2-4f59-8f8f-d1438486a5c5', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/2e070691-bd53-447e-80ad-2028d23400f1', 'Nogalix', 0, NULL, '2026-08-28 11:07:06');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('1f52f9ca-cd1e-4059-a4ba-37612c67c370', 10, 'cv', 'cv', 'CV « Nouveau CV » créé.', '/cv/c8cc2421-2cb0-49fc-9294-1237c1624d14', 'Nogalix', 0, NULL, '2026-08-28 11:10:52');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('44d26d9b-9574-4d54-be7e-146f1354e77a', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:36:56');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('f6da3437-2c8f-4c8b-add5-17cf906bc0c2', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:40:07');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('f0a91402-f84a-41cf-8976-76a3ce004258', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:43:41');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('84f94941-fd99-4be9-9fba-47552cf3135a', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:44:34');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('9cb70ec3-bab6-4553-a140-b8eb1806a84b', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:53:18');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('92d24982-859d-4a00-a33d-5ec313041572', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 11:59:54');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('d7eb1310-65cd-4d8d-8190-e5060514e9a7', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:06:00');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('53321cdb-af2e-4406-ac92-0ed400c7299f', 10, 'cv', 'cv', 'CV « CV · 🚀 **OFFRE D’EMPLOI – DÉVELOPPEUR WEB** » créé.', '/cv/ccab2b1f-3950-428b-90df-7e70aa99e3ec', 'Nogalix', 0, NULL, '2026-08-28 12:06:20');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('525bf4b5-2580-4069-8a19-e470627e308c', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:09:30');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('55942586-09a8-45cf-935c-52ba4f64211b', 10, 'cv', 'cv', 'CV « CV · 🚀 **OFFRE D’EMPLOI – DÉVELOPPEUR WEB** » créé.', '/cv/d5669b53-3124-4245-a2aa-fc555890c8a0', 'Nogalix', 0, NULL, '2026-08-28 12:09:38');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('5f73a55f-d96c-4a5f-b50b-777491f3ff92', 11, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-28 12:18:58');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('934533a1-f0e2-4cc3-8c8f-3f4e5cf19f90', 11, 'cv', 'cv', 'CV « CV Smoke » créé.', '/cv/f04f2fe6-f85a-42cc-af67-7e04413a4a59', 'Nogalix', 0, NULL, '2026-08-28 12:18:58');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('6de0718b-cd0c-4b7b-a9d5-6f422845fe57', 11, 'analyse', 'analyse', 'Analyse du CV « CV Smoke » : score 72/100 (Bon).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:18:58');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('2f2f7e24-ae4b-4ffc-9f54-65f8d5b14408', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:20:36');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('d104389b-f16e-4d22-8f86-ba3a5b824f70', 10, 'cv', 'cv', 'CV « CV · 🚀 **OFFRE D’EMPLOI – DÉVELOPPEUR WEB** » créé.', '/cv/e915a35b-2fcd-41d6-a9e3-2e40ea155800', 'Nogalix', 0, NULL, '2026-08-28 12:20:48');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('246060ac-e85c-40e3-af01-f4bc9e6b7d00', 12, 'systeme', 'systeme', 'Bienvenue sur Nogalix. Créez votre premier CV pour démarrer.', '/cv/nouveau', 'Nogalix', 0, NULL, '2026-08-28 12:28:12');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('4efd0d05-bfc0-4c6c-b678-37ff5178d200', 12, 'cv', 'cv', 'CV « CV Smoke » créé.', '/cv/50fd3e92-4150-4c09-9669-a18a113bc748', 'Nogalix', 0, NULL, '2026-08-28 12:28:13');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('5725cd54-84c4-4528-9716-fbe875ada865', 12, 'analyse', 'analyse', 'Analyse du CV « CV Smoke » : score 72/100 (Bon).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:28:13');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('211ae68e-1973-414a-b990-38570c588d99', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:29:22');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('2da2980a-455e-41a5-bc7c-206693643001', 10, 'cv', 'cv', 'CV « CV_TEGU_MBE_LOIC final » créé.', '/cv/7c20608b-9220-429c-b92b-3432ebfe7cbc', 'Nogalix', 0, NULL, '2026-08-28 12:29:33');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('30cc82a5-062e-4601-bb9c-4d786dfe6316', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:34:10');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('34ee0b33-29ed-4cbf-922c-2c0cccca8a97', 10, 'cv', 'cv', 'CV « CV_TEGU_MBE_LOIC final » créé.', '/cv/ae0ddba3-7fb6-4864-a5ce-d0adb4fb7093', 'Nogalix', 0, NULL, '2026-08-28 12:34:19');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('2a12cb06-2c4b-45c1-b478-f58ca3fe21ec', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:55:01');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('764f635d-f8e9-4b63-a52e-7e5f751a39a8', 10, 'cv', 'cv', 'CV « CV_TEGU_MBE_LOIC final » créé.', '/cv/1e798cf5-b8ea-4036-bfc3-f6547066e8b0', 'Nogalix', 0, NULL, '2026-08-28 12:55:13');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('cb9f6aef-d64f-4b46-a421-7f90d4a6c02d', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 12:59:45');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('d3f0f633-3d12-4287-8671-082309f86e16', 10, 'cv', 'cv', 'CV « CV_TEGU_MBE_LOIC final » créé.', '/cv/8d10630b-3bc8-475c-befe-dfcc98c9bc4e', 'Nogalix', 0, NULL, '2026-08-28 12:59:55');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('8ab1ce47-d498-457a-8d0d-255ae5d42463', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:08:56');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('fdd6e3a7-cb26-4755-90dd-60139131aecf', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:16:22');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('b222996a-437a-4ef2-aa88-8e43bd2a0212', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (72/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:20:28');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('a845b1e6-f1b9-4eb6-bfcb-78f274c37537', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (67/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:44:17');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('b6a143bb-06f9-4ce5-a095-aa4c4d85aee9', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (67/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:47:00');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('60bafaa1-376f-44c9-905c-8c72f883b770', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (67/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 13:59:37');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('24f0e35f-5125-4dc8-8cb3-3b964900f673', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Correspondance partielle. Modifiez votre CV pour vous rapprocher de l\'offre (67/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 14:05:33');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('7e6a630a-e87c-4127-a4cf-ed9ff500c707', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 14:28:19');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('e51fff28-73c6-4cc2-94d5-a668ec9da27f', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 14:33:30');
INSERT INTO `notifications` (`id`, `user_id`, `type`, `kind`, `message`, `href`, `actor`, `is_read`, `read_at`, `created_at`) VALUES ('9755be71-2628-4c22-80b1-505d29e0bc3c', 10, 'analyse', 'analyse', 'Comparaison CV / offre : Votre CV ne correspond pas encore à l\'offre (40/100).', '/analyse', 'Nogalix', 0, NULL, '2026-08-28 14:36:51');

DROP TABLE IF EXISTS `personal_access_tokens`;
CREATE TABLE `personal_access_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(80) NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `abilities` text,
  `last_used_at` datetime DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pat_token_hash` (`token_hash`),
  KEY `ix_personal_access_tokens_user_id` (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (1, 1, 'authToken', '8b7943cf2cf4d4c9ea0bc2a2123306b4f9d7020c58c9887447eb91baad8ca86a', NULL, '2026-08-27 13:23:37', '2026-08-28 13:23:37', '2026-08-27 13:23:37');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (2, 1, 'authToken', '8a069a38a7d573ff2923e35fb9d52cefe1def08834bea9529e0449642a986568', NULL, NULL, '2026-08-28 13:23:59', '2026-08-27 13:23:59');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (3, 2, 'authToken', '40df82dd6c1e5c0bfeeaefe13047c6bae5a27fb1de7fc1291efe5047e1c4683e', NULL, '2026-08-27 13:29:56', '2026-08-28 13:29:56', '2026-08-27 13:29:56');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (5, 3, 'authToken', '37fef45a5ffd9e31ae83b0d724ded46652bf59c4e686e3c000da152d8908bc04', NULL, '2026-08-27 15:55:02', '2026-08-28 15:54:55', '2026-08-27 15:54:55');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (6, 4, 'authToken', '91d6cdd873db7afec0787ad8b2b77112008b9ffe34b234d68b7abe04ff96048b', NULL, '2026-08-27 15:55:02', '2026-08-28 15:55:02', '2026-08-27 15:55:02');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (7, 5, 'authToken', '18db7d948b869649ea2f1e4fb73a2316395a3489330d1ba7a8e4a40719d5cc0c', NULL, NULL, '2026-08-28 16:16:29', '2026-08-27 16:16:29');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (8, 6, 'authToken', 'eff81cb86a85fcb86464e4a780852385ee237e5bdc02d886f20255f547a783b6', NULL, '2026-08-27 16:17:11', '2026-08-28 16:17:11', '2026-08-27 16:17:11');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (9, 7, 'authToken', '14f23a41f5fe3df026d735e93d3473b672c6a06652e1bbfdfcbe8abf9b795b9e', NULL, NULL, '2026-08-28 16:17:51', '2026-08-27 16:17:51');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (10, 8, 'authToken', '69f20359ad42e4bc4c541f8df2490d2ddbbc9a96df406676e8352a5f7f192c86', NULL, '2026-08-27 16:18:15', '2026-08-28 16:18:13', '2026-08-27 16:18:13');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (11, 9, 'authToken', '3c86473ea4d7614c916c1bd7c89e1609915ca7255065b61536e82b577a2f0a26', NULL, NULL, '2026-08-28 16:23:37', '2026-08-27 16:23:37');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (12, 10, 'authToken', '90746a5886cc282f1c7f2664bb11135f0f7688f8416bd0186a6deb8323db1d11', NULL, NULL, '2026-08-28 16:23:37', '2026-08-27 16:23:37');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (13, 10, 'authToken', '7ff6aac6a835140e9c25fa3094b078eba0c396e6aab603938092bf1ad8d255fe', NULL, '2026-08-27 16:30:39', '2026-08-28 16:30:39', '2026-08-27 16:30:39');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (14, 10, 'authToken', '78e9347110d1dd5ccbc418dd625bc7cf90d58e2b64f3b117079d17ac57d52b71', NULL, NULL, '2026-08-28 16:38:37', '2026-08-27 16:38:37');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (15, 10, 'authToken', '0525d4830ad6e4a720f4d00085341d08cf415422c8b77062d77b61380dfca2fe', NULL, '2026-08-27 16:39:15', '2026-08-28 16:39:13', '2026-08-27 16:39:13');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (16, 9, 'authToken', 'ee5dbafaab8704241638af512fe0a0a96d9f3fd95a5549e728e9a816e98b3123', NULL, '2026-08-27 16:39:16', '2026-08-28 16:39:16', '2026-08-27 16:39:16');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (17, 10, 'authToken', 'afae4c3ae5fbfa74b8ae0fa8b0a57ae26d18dd91977ecaefff00359ab21254a1', NULL, NULL, '2026-08-28 16:41:20', '2026-08-27 16:41:20');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (18, 10, 'authToken', '6e518c1b8f7b6c2d7dac2c0cd1b661d83bfaa56f575c0d6be34b95840a1d8e64', NULL, '2026-08-27 16:41:36', '2026-08-28 16:41:35', '2026-08-27 16:41:35');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (19, 9, 'authToken', '40e9cdb9e2cac2d979de631197a7f46c320e778399f505832fb481e14626758c', NULL, '2026-08-27 16:41:36', '2026-08-28 16:41:36', '2026-08-27 16:41:36');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (21, 11, 'authToken', 'fef38d61079f125bb36b4e5360055e592a5fced54cd03579be205963c9956787', NULL, '2026-08-28 12:18:58', '2026-08-29 12:18:58', '2026-08-28 12:18:58');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (23, 10, 'authToken', '7bcc9801cd64ef73fec0a9d928f82e829bb6555dde371c8bd37694bc2a09dfd6', NULL, '2026-08-28 13:46:58', '2026-08-29 12:20:24', '2026-08-28 12:20:24');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (24, 12, 'authToken', 'd8df974d6b6787602d3bbe6fbc923a685aae8bbdb2231a3e279bf3ee3ef806e8', NULL, '2026-08-28 12:28:12', '2026-08-29 12:28:12', '2026-08-28 12:28:12');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (26, 10, 'authToken', 'd2cd1b7a82c21463490c46471597ffcb83517a44a64a9c24d8045956968bbc99', NULL, '2026-08-28 14:10:46', '2026-08-29 13:58:53', '2026-08-28 13:58:53');
INSERT INTO `personal_access_tokens` (`id`, `user_id`, `name`, `token_hash`, `abilities`, `last_used_at`, `expires_at`, `created_at`) VALUES (27, 10, 'authToken', '21a39204b52b3b517c2ad276436f8927270d2bbc908a604088ec365f866ff0ab', NULL, '2026-08-28 14:39:56', '2026-08-29 14:27:57', '2026-08-28 14:27:57');

DROP TABLE IF EXISTS `plan_features`;
CREATE TABLE `plan_features` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL,
  `name` varchar(190) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `is_enabled` tinyint(1) NOT NULL DEFAULT '1',
  `sort_order` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `ix_plan_features_plan_id` (`plan_id`)
) ENGINE=MyISAM AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (1, 1, '1 CV', 'Créez et éditez un CV principal', 1, 0);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (2, 1, 'Modèles standards', 'Accès aux modèles non premium', 1, 1);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (3, 1, 'Analyse IA basique', 'Score et pistes d\'amélioration', 1, 2);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (4, 1, 'Export PDF', 'Via la boîte d\'impression du navigateur', 1, 3);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (5, 2, 'CV illimités', 'Créez autant de versions que nécessaire', 1, 0);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (6, 2, 'Tous les modèles premium', 'Accès complet à la galerie', 1, 1);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (7, 2, 'Analyse IA avancée', 'Audit ATS plus précis', 1, 2);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (8, 2, 'Édition à la voix', 'Complétez votre CV en dictant', 1, 3);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (9, 2, 'Lettres de motivation', 'Documents liés à vos candidatures', 1, 4);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (10, 2, 'Export PDF & Word', 'Formats adaptés aux recruteurs', 1, 5);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (11, 3, 'Tout dans Pro', 'Toutes les capacités du plan Pro', 1, 0);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (12, 3, 'Offres d\'emploi IA', 'Matching offres selon votre CV', 1, 1);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (13, 3, 'Optimisation ATS avancée', 'Recommandations ciblées offre par offre', 1, 2);
INSERT INTO `plan_features` (`id`, `plan_id`, `name`, `description`, `is_enabled`, `sort_order`) VALUES (14, 3, 'Support prioritaire', 'Réponses prioritaires de l\'équipe', 1, 3);

DROP TABLE IF EXISTS `plan_limitations`;
CREATE TABLE `plan_limitations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL,
  `key` varchar(120) NOT NULL,
  `limitation_type` varchar(30) NOT NULL,
  `value` int NOT NULL DEFAULT '0',
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_plan_limitation_key` (`plan_id`,`key`),
  KEY `ix_plan_limitations_plan_id` (`plan_id`)
) ENGINE=MyISAM AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (1, 1, 'cv.max', 'count', 1, '1 CV maximum');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (2, 1, 'templates.premium', 'boolean', 0, 'Modèles standards uniquement');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (3, 1, 'analyse.advanced', 'boolean', 0, 'Analyse IA basique');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (4, 1, 'assistant.voice', 'boolean', 0, 'Édition vocale non incluse');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (5, 1, 'documents.letters', 'boolean', 0, 'Lettres non incluses');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (6, 1, 'emploi.search', 'boolean', 0, 'Offres d\'emploi non incluses');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (7, 1, 'export.word', 'boolean', 0, 'Export PDF (impression) uniquement');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (8, 1, 'support.priority', 'boolean', 0, 'Support standard');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (9, 2, 'cv.max', 'count', -1, 'CV illimités');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (10, 2, 'templates.premium', 'boolean', 1, 'Tous les modèles premium');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (11, 2, 'analyse.advanced', 'boolean', 1, 'Analyse IA avancée');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (12, 2, 'assistant.voice', 'boolean', 1, 'Édition CV à la voix');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (13, 2, 'documents.letters', 'boolean', 1, 'Lettres de motivation');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (14, 2, 'emploi.search', 'boolean', 0, 'Offres d\'emploi réservées au Premium');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (15, 2, 'export.word', 'boolean', 1, 'Export PDF & Word');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (16, 2, 'support.priority', 'boolean', 0, 'Support standard');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (17, 3, 'cv.max', 'count', -1, 'CV illimités');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (18, 3, 'templates.premium', 'boolean', 1, 'Tous les modèles premium');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (19, 3, 'analyse.advanced', 'boolean', 1, 'Analyse ATS avancée');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (20, 3, 'assistant.voice', 'boolean', 1, 'Édition CV à la voix');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (21, 3, 'documents.letters', 'boolean', 1, 'Lettres de motivation');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (22, 3, 'emploi.search', 'boolean', 1, 'Recherche d\'offres IA');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (23, 3, 'export.word', 'boolean', 1, 'Export PDF & Word');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (24, 3, 'support.priority', 'boolean', 1, 'Support prioritaire');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (25, 1, 'candidature.generate', 'boolean', 0, 'Checklist candidature uniquement');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (26, 2, 'candidature.generate', 'boolean', 1, 'CV adapté à une offre');
INSERT INTO `plan_limitations` (`id`, `plan_id`, `key`, `limitation_type`, `value`, `description`) VALUES (27, 3, 'candidature.generate', 'boolean', 1, 'CV adapté à une offre');

DROP TABLE IF EXISTS `plans`;
CREATE TABLE `plans` (
  `id` int NOT NULL AUTO_INCREMENT,
  `slug` varchar(80) NOT NULL,
  `name` varchar(120) NOT NULL,
  `description` text,
  `tagline` varchar(190) DEFAULT NULL,
  `price` int NOT NULL DEFAULT '0',
  `duration_months` int NOT NULL DEFAULT '1',
  `level` int NOT NULL DEFAULT '1',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `highlighted` tinyint(1) NOT NULL DEFAULT '0',
  `popular` tinyint(1) NOT NULL DEFAULT '0',
  `cta` varchar(80) NOT NULL DEFAULT 'Choisir',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `ix_plans_slug` (`slug`)
) ENGINE=MyISAM AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `plans` (`id`, `slug`, `name`, `description`, `tagline`, `price`, `duration_months`, `level`, `is_active`, `highlighted`, `popular`, `cta`, `created_at`, `updated_at`) VALUES (1, 'gratuit', 'Gratuit', 'Pour commencer votre CV professionnel sans carte bancaire.', 'Pour commencer', 0, 1, 1, 1, 0, 0, 'Commencer', '2026-08-27 15:42:38', '2026-08-27 15:42:38');
INSERT INTO `plans` (`id`, `slug`, `name`, `description`, `tagline`, `price`, `duration_months`, `level`, `is_active`, `highlighted`, `popular`, `cta`, `created_at`, `updated_at`) VALUES (2, 'pro', 'Pro', 'Pour aller plus loin : modèles premium, voix et analyses avancées.', 'Pour aller plus loin', 4900, 1, 2, 1, 1, 0, 'Choisir Pro', '2026-08-27 15:42:39', '2026-08-27 15:42:39');
INSERT INTO `plans` (`id`, `slug`, `name`, `description`, `tagline`, `price`, `duration_months`, `level`, `is_active`, `highlighted`, `popular`, `cta`, `created_at`, `updated_at`) VALUES (3, 'premium', 'Premium', 'Pour se démarquer : emploi IA, support prioritaire et quotas élevés.', 'Pour se démarquer', 9900, 1, 3, 1, 0, 1, 'Choisir Premium', '2026-08-27 15:42:39', '2026-08-27 15:42:39');

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(190) NOT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `phone` varchar(40) DEFAULT NULL,
  `location` varchar(190) DEFAULT NULL,
  `avatar` varchar(500) DEFAULT NULL,
  `google_id` varchar(120) DEFAULT NULL,
  `has_google` tinyint(1) NOT NULL DEFAULT '0',
  `status` varchar(30) NOT NULL DEFAULT 'active',
  `email_verified_at` datetime DEFAULT NULL,
  `notify_email` tinyint(1) NOT NULL DEFAULT '1',
  `notify_jobs` tinyint(1) NOT NULL DEFAULT '1',
  `notify_analysis` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `reset_code` varchar(255) DEFAULT NULL,
  `reset_code_expires_at` datetime DEFAULT NULL,
  `plan_id` int DEFAULT NULL,
  `role` varchar(30) NOT NULL DEFAULT 'user',
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `google_id` (`google_id`),
  KEY `ix_users_email` (`email`),
  KEY `ix_users_plan_id` (`plan_id`),
  KEY `ix_users_role` (`role`)
) ENGINE=MyISAM AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (1, 'Test User', 'test.nogalix2@example.com', '$2b$12$YqZZeedz1UK.m01QVcJGHOl9Hg5LDeNC1iuZ1HlD8/wLNMy2QvtjG', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 13:23:37', 1, 1, 1, '2026-08-27 13:23:37', '2026-08-27 13:23:37', NULL, NULL, NULL, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (2, 'Ada Smoke', 'smoke_7083a549@example.com', '$2b$12$XVFEVu4cUt09uZ1u1pBp8e0232i8LcnZJQHRACfyZzmB23wM//Iw6', '670000000', 'Yaounde', NULL, NULL, 0, 'active', '2026-08-27 13:29:56', 1, 1, 1, '2026-08-27 13:29:56', '2026-08-27 13:29:56', NULL, NULL, NULL, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (3, 'Plan Check', 'plan.check.728179@example.com', '$2b$12$vCkExVANj4hqGQxQkJInVuj7hzQfpPIM76Ro3bHnAltJTYW9NElf2', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 15:54:55', 1, 1, 1, '2026-08-27 15:54:55', '2026-08-27 15:54:55', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (4, 'Prem Check', 'plan.prem.337041@example.com', '$2b$12$XYvb3p1370BSC6VchA8vCearmyyaT9jpoQI85abWKZStKq3ooYDES', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 15:55:02', 1, 1, 1, '2026-08-27 15:55:02', '2026-08-27 15:55:02', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (5, 'Cand User', 'cand.975338@example.com', '$2b$12$.XY.lKOpeJnk4T00GqZrdunOaLO9iPYzSrSfasd.TO38fml5cjg0.', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:16:29', 1, 1, 1, '2026-08-27 16:16:29', '2026-08-27 16:16:29', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (6, 'Cand User', 'cand.613589@example.com', '$2b$12$GpW9SRxzKG00c.2ypUz5zO/YsqW50njnWAvfom8bWB8hzdliJHPeK', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:17:11', 1, 1, 1, '2026-08-27 16:17:11', '2026-08-27 16:17:11', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (7, 'Cand User', 'cand.712294@example.com', '$2b$12$U92bM/y5fRWs4uML5d2Dfey0kf4aj/nNrS.ZShHq.50XkMn1t/HcW', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:17:51', 1, 1, 1, '2026-08-27 16:17:51', '2026-08-27 16:17:51', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (8, 'Cand User', 'cand.506799@example.com', '$2b$12$WSHmK9CwtKy72IVkHrIK/eqDq4Ag6008KM2qzHn34XMCrCdg6EwJW', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:18:13', 1, 1, 1, '2026-08-27 16:18:13', '2026-08-27 16:18:13', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (9, 'Utilisateur Demo', 'user.demo@nogalix.com', '$2b$12$eTF40DVpaiNWx6OMPyB1/e.RUGkUstDls5FQjlpS6kpbxZ/7nU1le', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:23:37', 1, 1, 1, '2026-08-27 16:23:37', '2026-08-27 16:23:37', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (10, 'Admin Nogalix', 'admin.demo@nogalix.com', '$2b$12$vpSsHpN0rPER925W/0puo.Uenn5Za.tXFtMCOhhDyoBjZtZny/VOC', NULL, NULL, NULL, NULL, 0, 'active', '2026-08-27 16:23:37', 1, 1, 1, '2026-08-27 16:23:37', '2026-08-27 16:23:37', NULL, NULL, 3, 'admin');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (11, 'Ada Smoke', 'smoke_d4d3ea82@example.com', '$2b$12$IFFQTMxIyy.bt.Fp1fWvFO3U3RoXLZqOr0DoKqzzUtbRYeHPz8nCi', '670000000', 'Yaounde', NULL, NULL, 0, 'active', '2026-08-28 12:18:58', 1, 1, 1, '2026-08-28 12:18:58', '2026-08-28 12:18:58', NULL, NULL, 1, 'user');
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `phone`, `location`, `avatar`, `google_id`, `has_google`, `status`, `email_verified_at`, `notify_email`, `notify_jobs`, `notify_analysis`, `created_at`, `updated_at`, `reset_code`, `reset_code_expires_at`, `plan_id`, `role`) VALUES (12, 'Ada Smoke', 'smoke_bea87481@example.com', '$2b$12$/g1DMnTvjO8BIh.otR.iQuJUaLULtyVHT0pOxPGktRVrpG8IgXLvG', '670000000', 'Yaounde', NULL, NULL, 0, 'active', '2026-08-28 12:28:12', 1, 1, 1, '2026-08-28 12:28:12', '2026-08-28 12:28:13', NULL, NULL, 1, 'user');

SET FOREIGN_KEY_CHECKS=1;
