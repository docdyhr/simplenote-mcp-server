# Changes in 1.17.2
*Released on 2026-07-14*

## ✨ Features

- fix MCP Resources metadata loss, add session-handoff prompt (#696) ([fc5d1275](../../commit/fc5d1275958ae7b9817f40e63531b5b970a61560))
- Vault — opt-in client-side note encryption (AES-256-GCM) (#695) ([2d63cc8a](../../commit/2d63cc8a8a09e1e377cca7c4332f1b5722b2b7ad))

## 🐛 Bug Fixes

- use project .venv consistently across eval tooling and dev scripts (#705) ([42990e92](../../commit/42990e92516221720fe57e128130bc4b3ca7eb94))
- close script-injection + npm supply-chain follow-ups (#703) ([cfff8e25](../../commit/cfff8e25b27d10b21b3928ccd0edea7bf69d02b2))
- correct malformed SHA-pinned action references from 879dfa9 (#702) ([9e6ab140](../../commit/9e6ab14013607fb7f171ceb6be7ba56f89d66546))
- resolve 2026-07-13 security & code quality audit findings (#699) ([b3df9b3a](../../commit/b3df9b3a146f1535335a5c6570d32dc9db18224c))
- read_resource crashed over the real MCP wire protocol (#698) ([19406fab](../../commit/19406fabad540536cd60149f8c2d7833205d787f))
- use Bandit-native nosec syntax instead of ruff's noqa for B105 (#697) ([673cd6fc](../../commit/673cd6fcd342af5b3764f28734c32accb911c10b))
- tag-space sanitization, search limit, sync re-indexing; refresh roadmap docs (#694) ([5facc899](../../commit/5facc8992129a562b913e1dca87e1d6d58b196e1))
- keychain persistent cache, ctypes token write, and async executor fixes (#680) ([4f722c6b](../../commit/4f722c6b3c1992637c37df58cdd96f0cc1d55172))
- persistent token file cache + async executor fixes (#661) ([c5be7c7b](../../commit/c5be7c7b65e6e75c2fd7d007bfb47d67417fbca2))
- Eliminate per-start keychain approval prompt ([4d342400](../../commit/4d342400b07f52d36489c0294d06bbb11d51a781))
- Simplenote v1.17.1 — keychain auth, fail-fast errors, quiet startup (#660) ([eff37c55](../../commit/eff37c554954fb7a3ab54ac8100a806cbb2a2ebd))
- scope claude-dependabot-merge push trigger to main branch only (#659) ([6dac5135](../../commit/6dac513580b1533052212c49a9126427bb6cd0cc))

## 📚 Documentation

- address Sourcery follow-ups from PR #703 (#704) ([414d3bb7](../../commit/414d3bb74439286636bf8b7d5c73993d03df7673))

## 👷 Continuous Integration

- **deps**: bump actions/cache from 5 to 6 in /.github/workflows (#670) ([85418874](../../commit/85418874c19aff80014af57f763f663e5d6527bd))

## 🔧 Chores

- **deps**: bump the npm_and_yarn group across 1 directory with 7 updates (#701) ([f55be3d2](../../commit/f55be3d29942a1362eef148bc5818d75980a389c))

## ⬆️ Dependencies

- **deps**: bump virtualenv from 21.5.1 to 21.6.1 (#692) ([0135d269](../../commit/0135d2692f9508cda2cead4036e26486a8bfa23a))
- **deps**: bump ruff from 0.15.20 to 0.15.21 (#690) ([0e8d5198](../../commit/0e8d51980ea4462fc3d45dad6a6d4fc11bc0593a))
- **deps**: bump regex from 2026.6.28 to 2026.7.10 (#693) ([6f18e633](../../commit/6f18e6337171a50e922867df31468385e16eda5f))
- **deps**: bump build from 1.5.0 to 1.5.1 (#691) ([085d606d](../../commit/085d606d486c6308bccbaf286ad9d383a6e54372))
- **deps**: bump nltk from 3.9.4 to 3.10.0 (#689) ([3d5c2079](../../commit/3d5c2079b14b178a7bef9963d68b80f9123465ce))
- **deps**: bump cffi from 2.0.0 to 2.1.0 (#688) ([c8a7b0b6](../../commit/c8a7b0b6f28c459e0d70cd57eb6653db22e410ad))
- **deps**: bump uvicorn from 0.50.0 to 0.51.0 (#687) ([ed272049](../../commit/ed27204991cff36b6e6320c2822b200e841baa4a))
- **deps**: bump tqdm from 4.68.3 to 4.68.4 (#686) ([c51b4639](../../commit/c51b46397e75e26d4a82841162682c011c3c3724))
- **deps**: bump charset-normalizer from 3.4.7 to 3.4.9 (#685) ([e561859c](../../commit/e561859c91e4659b574905e864e87327f36c727f))
- **deps**: bump mkdocstrings from 1.0.4 to 1.0.6 (#684) ([04a98484](../../commit/04a98484cfddf0a210ff06d8211eea99a9b8a4d0))
- **deps**: bump mypy from 2.1.0 to 2.2.0 (#683) ([bb9ceadd](../../commit/bb9ceaddd9dfc2ce391ca0d395138e79cfd27d87))
- **deps**: bump librt from 0.12.0 to 0.13.0 (#682) ([d064cd31](../../commit/d064cd310d03510ddd8c4867bfca0404bdb43997))
- **deps**: bump filelock from 3.29.5 to 3.29.7 (#681) ([ca29c036](../../commit/ca29c0367c24304c2c2ef0038abb6489428c0c02))
- **deps**: bump setuptools from 82.0.1 to 83.0.0 (#677) ([6e11d334](../../commit/6e11d3341b9bb698e2d86ef7e76af58ae4761c56))
- **deps**: bump typing-extensions from 4.15.0 to 4.16.0 (#679) ([1ec2d396](../../commit/1ec2d396fa9b059b2729fb178acf997d68bec497))
- **deps**: bump filelock from 3.29.4 to 3.29.5 (#678) ([90fb95a0](../../commit/90fb95a08aafc944df22e3c0af88b133cecebc21))
- **deps**: bump regex from 2026.5.9 to 2026.6.28 (#676) ([b45b497b](../../commit/b45b497b4579a0f8717031a304b2f002a61f3f1f))
- **deps**: bump pymdown-extensions from 11.0 to 11.0.1 (#675) ([1e23014b](../../commit/1e23014b174c302923bc560e2c3f7e12b5858a2b))
- **deps**: bump coverage from 7.14.3 to 7.15.0 (#674) ([f0d640ef](../../commit/f0d640efc00ae8d348cb58775cc60d61c0fe9a4a))
- **deps**: bump aiohappyeyeballs from 2.6.2 to 2.7.1 (#673) ([4a39da2d](../../commit/4a39da2dd2e1b89823251bb435d8fe13cf53d832))
- **deps**: bump librt from 0.11.0 to 0.12.0 (#672) ([15359f42](../../commit/15359f4227eee4e61a466e38d885b1ebe3113596))
- **deps**: bump uvicorn from 0.49.0 to 0.50.0 (#671) ([605414ea](../../commit/605414ead726949490e44aaa71fd944921d5520a))
- **deps**: bump pymdown-extensions from 10.21.3 to 11.0 (#663) ([37cd8260](../../commit/37cd8260daae72941cf2c0f6e980cba12f351282))
- **deps**: bump nh3 from 0.3.5 to 0.3.6 (#669) ([388748d4](../../commit/388748d4f11d641a7ccb0eda39c1205bc33b4415))
- **deps**: bump coverage from 7.14.2 to 7.14.3 (#668) ([967a70b9](../../commit/967a70b9276ade6e322a74cc9703200e06dc96c6))
- **deps**: bump typer from 0.26.7 to 0.26.8 (#667) ([88880dc0](../../commit/88880dc05b30ea3036a751f05e0a5a3c93c5b0a7))
- **deps**: bump anyio from 4.14.0 to 4.14.1 (#666) ([67bc33c2](../../commit/67bc33c2ed8b16af8e76ef8f83447b5bc843c0d2))
- **deps**: bump click from 8.4.1 to 8.4.2 (#665) ([41809351](../../commit/41809351cfac72a4ec31000e53b035db7656fcd9))
- **deps**: bump ruff from 0.15.18 to 0.15.20 (#664) ([71179a1c](../../commit/71179a1c60fe7258253a9c4903bec26f7ab94963))
- **deps**: bump mcp in the production-dependencies group (#662) ([97e699ad](../../commit/97e699ad9eec0c95d0b1b219894fb280a0f99653))
