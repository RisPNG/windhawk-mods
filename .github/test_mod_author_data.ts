import assert from 'node:assert/strict';
import test from 'node:test';
import { validateAndUpdateAuthorData, validateModAuthorData } from '../deploy.ts';

test('author history accepts display-name changes and equivalent profile URLs', () => {
    const authors: Parameters<typeof validateModAuthorData>[0] = {};
    validateAndUpdateAuthorData('blur', 'newer', {
        github: 'HTTPS://GitHub.COM/RisPNG/',
        author: 'A new display name',
        twitter: 'https://x.com/Example/',
    }, authors);
    validateAndUpdateAuthorData('blur', 'older', {
        github: 'https://github.com/rispng',
        author: 'An old display name',
        twitter: 'HTTPS://Twitter.COM/example',
    }, authors);
    assert.deepEqual(Object.keys(authors), ['https://github.com/rispng']);
    assert.equal(authors['https://github.com/rispng'].author, 'A new display name');
    assert.equal(authors['https://github.com/rispng'].twitter, 'https://x.com/example');
    validateModAuthorData(authors);
});

test('different GitHub accounts may use the same display name', () => {
    const authors: Parameters<typeof validateModAuthorData>[0] = {};
    for (const account of ['first', 'second']) {
        validateAndUpdateAuthorData('blur', 'commit', {
            github: `https://github.com/${account}`,
            author: 'A shared display name',
        }, authors);
    }
    validateModAuthorData(authors);
    assert.equal(Object.keys(authors).length, 2);
});

test('an author cannot change the linked Twitter identity across history', () => {
    const authors: Parameters<typeof validateModAuthorData>[0] = {};
    validateAndUpdateAuthorData('blur', 'newer', {
        github: 'https://github.com/rispng', author: 'Name', twitter: 'https://x.com/first',
    }, authors);
    assert.throws(() => validateAndUpdateAuthorData('blur', 'older', {
        github: 'https://github.com/rispng', author: 'Name', twitter: 'https://x.com/second',
    }, authors));
});

test('canonical GitHub and Twitter identities cannot be assigned to different author records', () => {
    for (const authors of [
        {
            first: { github: 'https://github.com/example', author: 'First', homepages: [] },
            second: { github: 'HTTPS://GitHub.COM/Example/', author: 'Second', homepages: [] },
        },
        {
            first: { github: 'https://github.com/first', author: 'First', homepages: [], twitter: 'https://x.com/example' },
            second: { github: 'https://github.com/second', author: 'Second', homepages: [], twitter: 'HTTPS://Twitter.COM/Example/' },
        },
    ]) {
        assert.throws(() => validateModAuthorData(authors));
    }
});
